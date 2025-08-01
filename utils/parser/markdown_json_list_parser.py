import json
import re
from typing import Any, Dict, List, Optional, Sequence, Union

from agentscope.models import ModelResponse
from agentscope.parsers.parser_base import DictFilterMixin, ParserBase
from agentscope.service import ServiceExecStatus, ServiceResponse

from config.logger import logger
from utils.react_tool.toolkit import extract_json_block, format_json_diagnosis

def extract_code_blocks(text: str, tag: str = "json") -> list[str]:
    pattern = rf"```{tag}\s*([\s\S]*?)```"
    return re.findall(pattern, text, re.IGNORECASE)


def sanitize_json_quotes(json_str: str) -> str:
    """
    替换所有中文引号和非法符号为英文双引号
    
    Args:
        json_str (str): 原始JSON字符串
        
    Returns:
        str: 清洗后的JSON字符串
    """
    # 替换中文双引号（全角）和各种其他中文引号
    json_str = re.sub(r'[“”〝〞『』「」]', '"', json_str)
    json_str = re.sub(r'[‘’]', '"', json_str)
    # 替换错用的单引号
    json_str = json_str.replace("'", '"')
    # 替换全角冒号
    json_str = json_str.replace("：", ":")
    # 替换错误逗号
    json_str = json_str.replace("，", ",")
    # 替换全角括号
    json_str = json_str.replace("（", "(")
    json_str = json_str.replace("）", ")")
    # 替换全角井号
    json_str = json_str.replace("＃", "#")
    return json_str


def clean_json_string(json_str: str) -> str:
    """清洗JSON字符串，修复常见问题"""
    logger.debug(f"清洗前的JSON字符串: {json_str}")
    
    # 保存原始字符串用于比较
    original_json_str = json_str
    
    # 修复转义字符问题，特别是换行符
    json_str = json_str.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
    
    # 修复多余的控制字符
    json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', json_str)
    
    # 为没有引号的字符串值添加引号
    json_str = re.sub(r'(:\s*)([^\d\[\{\]\}\s"\'"][^,}\n]*?)([,\n}])', 
                     lambda m: f'{m.group(1)}"{m.group(2).strip()}"{m.group(3)}' 
                     if not (m.group(2).strip().lower() in ['true', 'false', 'null'] or 
                             re.match(r'^\d+\.?\d*$', m.group(2).strip()))
                     else f'{m.group(1)}{m.group(2).strip()}{m.group(3)}', 
                     json_str)
    
    return json_str


def fix_json_format(json_str: str) -> str:
    """修复常见的JSON格式错误"""
    logger.debug(f"修复前的JSON字符串: {json_str}")
    
    # 使用专门的函数处理引号
    json_str = sanitize_json_quotes(json_str)
    
    # 移除行内注释（以//开头的注释）
    lines = json_str.split('\n')
    cleaned_lines = []
    for line in lines:
        # 移除行内注释，但要避免移除URL中的//
        # 简单的启发式方法：如果//前面没有引号或者引号是成对的，则认为是注释
        if '//' in line:
            # 检查引号是否成对
            single_quotes = line.count("'")
            double_quotes = line.count('"')
            # 如果引号不成对，则可能包含注释
            if single_quotes % 2 == 0 and double_quotes % 2 == 0:
                # 移除注释部分
                comment_index = line.find('//')
                if comment_index != -1:
                    line = line[:comment_index]
        cleaned_lines.append(line)
    
    json_str = '\n'.join(cleaned_lines)
    
    # 移除控制字符（除了制表符、换行符和回车符）
    original_json_str = json_str
    json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', json_str)
    if json_str != original_json_str:
        logger.debug("已移除控制字符")
    
    # 替换中文引号为英文引号（多次替换以确保所有情况都被处理）
    original_json_str = json_str
    # 使用更全面的中文引号匹配模式
    json_str = re.sub(r'[“”〝〞『』「」]', '"', json_str)
    json_str = re.sub(r'[‘’]', "'", json_str)
    if json_str != original_json_str:
        logger.debug("已替换中文引号为英文引号")
    
    # 修复键中的换行符和多余空格
    original_json_str = json_str
    json_str = re.sub(r'"\s*\n\s*"', '""', json_str)  # 修复被换行符分隔的空字符串键
    json_str = re.sub(r'(\w)\s*\n\s*:', r'\1":', json_str)  # 修复键后换行的情况
    json_str = re.sub(r':\s*\n\s*"', r':"', json_str)  # 修复值前换行的情况
    if json_str != original_json_str:
        logger.debug("已修复键和值中的换行符")
    
    # 修复非法键名（如 (continue) 或 [suggest] 等）
    original_json_str = json_str
    json_str = re.sub(r'"$\s*([a-zA-Z_]\w*)\s*$"', r'"\1"', json_str)  # 修复 (key) 格式
    json_str = re.sub(r'"\[\s*([a-zA-Z_]\w*)\s*\]"', r'"\1"', json_str)  # 修复 [key] 格式
    if json_str != original_json_str:
        logger.debug("已修复非法键名")
    
    # 修复混合引号问题（单引号和双引号混用）
    original_json_str = json_str
    
    # 将单引号包裹的键转换为双引号
    json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
    
    # 将单引号包裹的值转换为双引号（仅当值不是数字、布尔值或null时）
    def replace_single_quotes(match):
        value = match.group(1)
        # 检查是否为数字、布尔值或null
        if (value.lower() in ['true', 'false', 'null'] or 
            re.match(r'^\d+\.?\d*$', value)):
            return f': {value}'
        else:
            return f': "{value}"'
    
    json_str = re.sub(r':\s*\'([^\']*)\'', replace_single_quotes, json_str)
    if json_str != original_json_str:
        logger.debug("已修复混合引号问题")
    
    # 修复缺失的引号（简单的启发式方法）
    # 匹配类似 key: "value" 的模式，给key加上引号
    original_json_str = json_str
    json_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', json_str)
    if json_str != original_json_str:
        logger.debug("已修复缺失的键引号")
    
    # 修复没有引号的键值对（键没有引号，值可能有引号可能没有）
    original_json_str = json_str
    json_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)(\s*)([^"\'\d\[\{\]\}\s][^,}\n]*?|[^\s,}\n]*?)([,\n}])', 
                      lambda m: f'{m.group(1)}"{m.group(2)}"{m.group(3)}{m.group(4)}"{m.group(5)}"{m.group(6)}' 
                      if not (m.group(5).lower() in ['true', 'false', 'null'] or re.match(r'^\d+\.?\d*$', m.group(5))) 
                      else f'{m.group(1)}"{m.group(2)}"{m.group(3)}{m.group(4)}{m.group(5)}{m.group(6)}', 
                      json_str)
    if json_str != original_json_str:
        logger.debug("已修复没有引号的键值对")
    
    # 修复缺失值的注释符号
    original_json_str = json_str
    json_str = re.sub(r'#(.*?)#', r'"\1"', json_str)
    if json_str != original_json_str:
        logger.debug("已修复特殊注释符号")
    
    # 修复没有引号的键值对
    # 匹配类似 "key": value 的模式，给value加上引号（如果value不是数字、布尔值或null）
    # 避免匹配已经用引号括起来的值
    def quote_value(match):
        value = match.group(2).strip()
        # 检查是否为数字、布尔值或null
        if (value.lower() in ['true', 'false', 'null'] or 
            re.match(r'^\d+\.?\d*$', value)):
            return match.group(0)
        else:
            # 移除值中的换行符和多余空格
            value = re.sub(r'\s+', ' ', value)
            logger.debug(f"为值添加引号: {value}")
            return f'{match.group(1)}"{value}"{match.group(3)}'
    
    original_json_str = json_str
    json_str = re.sub(
        r'(:\s*)([^"\'\d\[\{\]\}\s][^,}\n]*?)([,\n}])', 
        quote_value,
        json_str
    )
    if json_str != original_json_str:
        logger.debug("已修复缺失的值引号")
    
    logger.debug(f"修复后的JSON字符串: {json_str}")
    return json_str


def try_complete_json(json_str: str) -> str:
    """
    尝试补全被截断的JSON字符串
    
    Args:
        json_str (str): 可能被截断的JSON字符串
        
    Returns:
        str: 补全后的JSON字符串
    """
    # 检查是否缺少结尾括号
    open_brackets = json_str.count('[')
    close_brackets = json_str.count(']')
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    
    # 尝试补全缺失的括号
    if open_brackets > close_brackets:
        json_str += ']' * (open_brackets - close_brackets)
    
    if open_braces > close_braces:
        json_str += '}' * (open_braces - close_braces)
    
    return json_str

def extract_clean_json(raw_output: str) -> Union[List[Dict[str, Any]], None]:
    """
    尝试从 LLM 返回的字符串中提取并清洗 JSON。
    
    处理顺序：
    1. 提取 JSON 代码块（```json ... ```)
    2. 使用 format_json_diagnosis 做字段校验与格式标准化
    3. 若失败，执行 fallback：替换中文引号 + 去除 markdown 包裹 + 直接 json.loads

    Args:
        raw_output (str): 模型输出文本

    Returns:
        List[Dict[str, Any]] or None
    """
    if not raw_output.strip():
        logger.warning("extract_clean_json: 输入为空")
        return None

    # Step 1: 提取 JSON 代码块
    extract_res = extract_json_block(raw_output)
    raw_json_str = extract_res.content if extract_res.status == ServiceExecStatus.SUCCESS else raw_output

    # Step 2: 使用格式化工具处理
    fmt_res = format_json_diagnosis(raw_json_str)
    if fmt_res.status == ServiceExecStatus.SUCCESS:
        logger.info("extract_clean_json: 使用 format_json_diagnosis 成功")
        return fmt_res.content

    # Step 3: 尝试使用repair_broken_json修复
    repair_res = repair_broken_json(raw_json_str)
    if repair_res.status == ServiceExecStatus.SUCCESS:
        logger.info("extract_clean_json: 使用 repair_broken_json 成功")
        # 验证结果是列表
        if isinstance(repair_res.content, list):
            return repair_res.content

    # Step 4: fallback 尝试清洗和直接 json.loads
    try:
        fallback_cleaned = re.sub(r"[‘’“”]", '"', raw_output)  # 替换中文引号
        fallback_cleaned = re.sub(r"```json|```", "", fallback_cleaned).strip()
        fallback_result = json.loads(fallback_cleaned)

        if isinstance(fallback_result, list):
            logger.warning("extract_clean_json: fallback 解析成功")
            return fallback_result
        else:
            logger.error("extract_clean_json: fallback 结果不是列表")
    except Exception as e:
        logger.error(f"extract_clean_json: fallback 解析失败: {e}")

    logger.error("extract_clean_json: 所有解析方式失败")
    return None

class MarkdownJsonListParser(ParserBase, DictFilterMixin):
    def __init__(
        self,
        content_hint: Optional[dict[str, str]] = None,
        required_keys: Optional[list[str]] = None,
        keys_to_memory: Union[str, bool, Sequence[str]] = True,
        keys_to_content: Union[str, bool, Sequence[str]] = True,
        keys_to_metadata: Union[str, bool, Sequence[str]] = False,
    ):
        self.content_hint = content_hint
        self.required_keys = required_keys or []
        
        # Initialize the mixin class to allow filtering the parsed response
        DictFilterMixin.__init__(
            self,
            keys_to_memory=keys_to_memory,
            keys_to_content=keys_to_content,
            keys_to_metadata=keys_to_metadata,
        )

    @property
    def format_instruction(self) -> str:
        hint_str = "\n".join(
            [f'- "{key}": {desc}' for key, desc in (self.content_hint or {}).items()]
        )
        return f"""请以以下格式输出内容：
```json
[
  {{
    "disease": "疾病名称",
    "p": "置信度（0~1）",
    "base": "初步建议",
    "continue": "持续建议",
    "suggest": "重度建议"
  }}
]
```
每个字段含义如下：
{hint_str}
确保：
1. 所有字段都用双引号括起来
2. 所有字符串值都用双引号括起来
3. 不使用中文引号（“”）
4. 置信度使用0到1之间的数值
5. 每个诊断项都包含所有必需字段
6. 不要包含注释
7. 确保JSON语法正确，可以被标准JSON解析器解析
8. 不要在键或值中包含换行符
9. 不要使用特殊符号包裹键名，如 (key) 或 [key]
10. 使用完整键名，不要使用缩写（如使用"disease"而不是"d"）
11. 每个诊断项必须是一个完整的对象，包含所有5个字段
12. 不要输出任何不完整的对象或缺少字段的对象
13. 键名前后不能有括号或其他特殊符号
14. 所有键名必须使用英文字符，不要使用中文字符作为键名
"""

    def parse(self, response: ModelResponse) -> ModelResponse:
        """Parse the response text to a JSON list object, and fill it in the parsed
        field in the response object."""
        # 获取文本内容
        if response.text is None:
            # Raise this error to the developer
            raise ValueError(
                "The text field of the response is `None`",
            )
        
        logger.debug(f"原始响应文本: {response.text}")
        
        # 提取代码块中的内容
        blocks = extract_code_blocks(response.text, tag="json")
        if not blocks:
            logger.warning("未找到JSON代码块")
            response.parsed = None
            response.success = False
            return response
            
        logger.debug(f"提取的JSON代码块: {blocks[0]}")
            
        try:
            # 尝试直接解析
            parsed = json.loads(blocks[0])
            logger.debug("JSON直接解析成功")
        except json.JSONDecodeError as e:
            logger.warning(f"JSON直接解析失败: {e}")
            # 如果直接解析失败，尝试修复格式后再解析
            try:
                fixed_json = fix_json_format(blocks[0])
                parsed = json.loads(fixed_json)
                logger.debug("JSON修复后解析成功")
                # 如果修复后能成功解析，记录日志
            except json.JSONDecodeError as e:
                logger.error(f"JSON修复后仍然解析失败: {e}")
                # 尝试使用清洗函数再次处理
                try:
                    cleaned_json = clean_json_string(blocks[0])
                    parsed = json.loads(cleaned_json)
                    logger.debug("JSON清洗后解析成功")
                except json.JSONDecodeError as e:
                    logger.error(f"JSON清洗后仍然解析失败: {e}")
                    # 尝试补全JSON后再次解析
                    try:
                        completed_json = try_complete_json(blocks[0])
                        cleaned_json = clean_json_string(completed_json)
                        parsed = json.loads(cleaned_json)
                        logger.debug("JSON补全并清洗后解析成功")
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON补全并清洗后仍然解析失败: {e}")
                        # 最后尝试使用专门的引号清洗函数
                        try:
                            sanitized_json = sanitize_json_quotes(blocks[0])
                            parsed = json.loads(sanitized_json)
                            logger.debug("JSON引号清洗后解析成功")
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON引号清洗后仍然解析失败: {e}")
                            response.parsed = None
                            response.success = False
                            return response
        
        # 验证解析结果
        if not isinstance(parsed, list):
            logger.warning(f"解析结果不是列表类型: {type(parsed)}")
            response.parsed = None
            response.success = False
            return response
            
        # 对于列表中的每个项目，尝试修复并验证
        validated_items = []
        for i, item in enumerate(parsed):
            if not isinstance(item, dict):
                # 如果不是字典，跳过该项
                logger.warning(f"项目 {i} 不是字典类型: {type(item)}")
                continue
                
            # 检查必需的键是否存在
            if self.required_keys:
                missing_keys = [k for k in self.required_keys if k not in item]
                if missing_keys:
                    logger.warning(f"项目 {i} 缺少必需键: {missing_keys}")
                    # 如果有缺失的键，尝试修复
                    # 这里我们只记录日志，但仍然将项目添加到结果中
            
            validated_items.append(item)
        
        # 成功解析
        logger.debug(f"最终解析结果: {validated_items}")
        response.parsed = validated_items
        response.success = True
        return response