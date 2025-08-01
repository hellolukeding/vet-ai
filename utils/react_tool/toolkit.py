import json
import re
from typing import Any

from agentscope.service import (ServiceExecStatus, ServiceResponse,
                                ServiceToolkit)

from config.logger import logger


def clean_json_string(json_str: str) -> str:
    """清洗JSON字符串，修复常见问题"""
    logger.debug(f"清洗前的JSON字符串: {json_str}")
    
    # 保存原始字符串用于比较
    original_json_str = json_str
    
    # 修复转义字符问题，特别是换行符
    json_str = json_str.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
    
    # 修复多余的控制字符
    json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', json_str)
    
    # 修复键中的换行符和多余空格
    json_str = re.sub(r'"\s*\n\s*"', '""', json_str)  # 修复被换行符分隔的空字符串键
    json_str = re.sub(r'"(\w+)\s*\n\s*"', r'"\1"', json_str)  # 修复键中的换行
    json_str = re.sub(r'"\s*\n\s*([^"]+)"', r'"\1"', json_str)  # 修复键中的换行和空格
    
    # 修复值中的换行符
    json_str = re.sub(r'(:\s*)"\s*\n\s*([^"]*)\s*\n\s*"', r'\1"\2"', json_str)
    
    # 修复键名中的空格和换行
    json_str = re.sub(r'"([^"]*)\s*\n\s*([^"]*)"', r'"\1\2"', json_str)
    json_str = re.sub(r'"([^"]*)\s+([^"]*)"', r'"\1 \2"', json_str)
    
    # 为没有引号的字符串值添加引号
    json_str = re.sub(r'(:\s*)([^\d\[\{\]\}\s"\'"][^,}\n]*?)([,\n}])', 
                     lambda m: f'{m.group(1)}"{m.group(2).strip()}"{m.group(3)}' 
                     if not (m.group(2).strip().lower() in ['true', 'false', 'null'] or 
                             re.match(r'^\d+\.?\d*$', m.group(2).strip()))
                     else f'{m.group(1)}{m.group(2).strip()}{m.group(3)}', 
                     json_str)
    
    return json_str


def format_json_diagnosis(raw_json_str: str) -> ServiceResponse:
    """
    格式化诊断JSON字符串，修复各种格式问题
    
    Args:
        raw_json_str (str): 原始JSON字符串
        
    Returns:
        ServiceResponse: 包含格式化后JSON的响应
    """
    try:
        # 检查输入是否为空
        if not raw_json_str or not raw_json_str.strip():
            return ServiceResponse(
                status=ServiceExecStatus.ERROR,
                content={"error": "输入的JSON字符串为空"}
            )
        
        # 如果输入是被引号包裹的字符串，先去除外层引号
        cleaned_input = raw_json_str.strip()
        if cleaned_input.startswith("'") and cleaned_input.endswith("'"):
            cleaned_input = cleaned_input[1:-1]
        elif cleaned_input.startswith('"') and cleaned_input.endswith('"'):
            cleaned_input = cleaned_input[1:-1]
        
        # 使用现有的清洗函数
        cleaned_json = clean_json_string(cleaned_input)
        
        # 进一步清理：移除开头和结尾的空白字符
        cleaned_json = cleaned_json.strip()
        
        # 尝试解析
        parsed_result = json.loads(cleaned_json)
        
        # 验证结果是列表
        if not isinstance(parsed_result, list):
            return ServiceResponse(
                status=ServiceExecStatus.ERROR,
                content={"error": "解析结果不是列表类型", "actual_type": type(parsed_result).__name__}
            )
        
        # 验证每个项目
        validated_items = []
        for i, item in enumerate(parsed_result):
            if not isinstance(item, dict):
                logger.warning(f"跳过非字典类型的诊断项 {i}: {item}")
                continue
                
            # 确保必需字段存在
            required_keys = ["disease", "p", "base", "continue", "suggest"]
            for key in required_keys:
                # 检查键是否为字符串类型
                if not isinstance(key, str):
                    logger.warning(f"项目 {i} 的键不是字符串类型: {type(key)}")
                    continue
                    
                if key not in item:
                    # 尝试修复缩写字段
                    if key == "disease" and "d" in item:
                        item["disease"] = item.pop("d")
                    elif key == "p" and "prob" in item:
                        item["p"] = item.pop("prob")
                    elif key == "suggest" and "sugg" in item:
                        item["suggest"] = item.pop("sugg")
                    else:
                        item[key] = f"缺失的{key}字段"
                        logger.warning(f"项目 {i} 缺少必需字段 {key}，已用默认值填充")
            
            # 确保置信度在有效范围内
            try:
                item["p"] = float(item["p"])
                if not (0 <= item["p"] <= 1):
                    original_p = item["p"]
                    item["p"] = max(0, min(1, item["p"]))
                    logger.warning(f"项目 {i} 的置信度值 {original_p} 超出有效范围，已调整为 {item['p']}")
            except (ValueError, TypeError):
                item["p"] = 0.5
                logger.warning(f"项目 {i} 的置信度格式无效，已设置默认值 0.5")
                
            # 处理可选的药物相关字段
            optional_med_fields = [
                "base_medicine", "base_medicine_usage", 
                "continue_medicine", "continue_medicine_usage",
                "suggest_medicine", "suggest_medicine_usage"
            ]
            
            for field in optional_med_fields:
                if field not in item:
                    item[field] = ""
            
            validated_items.append(item)
        
        return ServiceResponse(
            status=ServiceExecStatus.SUCCESS,
            content=validated_items
        )
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}")
        logger.error(f"原始JSON字符串: {repr(raw_json_str)}")
        logger.error(f"清洗后的JSON字符串: {repr(cleaned_json) if 'cleaned_json' in locals() else '未生成'}")
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content={"error": f"JSON解析失败: {str(e)}", "raw_input": raw_json_str}
        )
    except Exception as e:
        logger.error(f"格式化JSON诊断时出错: {e}", exc_info=True)
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content={"error": str(e), "raw_input": raw_json_str}
        )


def extract_json_block(text: str) -> ServiceResponse:
    """
    从文本中提取JSON代码块
    
    Args:
        text (str): 包含JSON代码块的文本
        
    Returns:
        ServiceResponse: 包含提取的JSON字符串的响应
    """
    try:
        # 检查输入是否为空
        if not text or not text.strip():
            return ServiceResponse(
                status=ServiceExecStatus.ERROR,
                content={"error": "输入文本为空"}
            )
        
        pattern = r"```json\s*([\s\S]*?)```"
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        if matches:
            extracted_json = matches[0]
            logger.debug(f"成功提取JSON代码块: {extracted_json[:100]}...")
            return ServiceResponse(
                status=ServiceExecStatus.SUCCESS,
                content=extracted_json
            )
        else:
            # 如果没有找到代码块，尝试直接解析整个文本
            logger.debug("未找到JSON代码块，将尝试直接解析整个文本")
            return ServiceResponse(
                status=ServiceExecStatus.SUCCESS,
                content=text
            )
    except Exception as e:
        logger.error(f"提取JSON代码块时出错: {e}", exc_info=True)
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content={"error": str(e), "raw_input": text}
        )


def repair_broken_json(text: str) -> ServiceResponse:
    """
    尝试修复格式错误或被破坏的 JSON 字符串。

    Args:
        text (str): 原始 JSON 字符串或 JSON 样式的文本

    Returns:
        ServiceResponse: 包含修复后 JSON 的结果或错误信息
    """
    try:
        if not text or not text.strip():
            return ServiceResponse(
                status=ServiceExecStatus.ERROR,
                content={"error": "输入为空"}
            )

        # 去除 markdown 包裹
        text = text.strip().strip("`").strip()

        # 替换中文引号和其他非标准引号为英文双引号
        text = (
            text.replace("“", '"').replace("”", '"')
                .replace("‘", '"').replace("’", '"')
                .replace("‟", '"').replace("″", '"')
                .replace("«", '"').replace("»", '"')
                .replace("＂", '"')
        )

        # 修复键中的换行符和多余空格
        text = re.sub(r'"\s*\n\s*"', '""', text)  # 修复被换行符分隔的空字符串键
        text = re.sub(r'"(\w+)\s*\n\s*"', r'"\1"', text)  # 修复键中的换行
        text = re.sub(r'"\s*\n\s*([^"]+)"', r'"\1"', text)  # 修复键中的换行和空格
        
        # 修复值中的换行符
        text = re.sub(r'(:\s*)"\s*\n\s*([^"]*)\s*\n\s*"', r'\1"\2"', text)
        
        # 修复错用的冒号（中文冒号）
        text = re.sub(r'“([^"]+)”\s*：', r'"\1":', text)
        
        # 修复键名中的空格和换行
        text = re.sub(r'"([^"]*)\s*\n\s*([^"]*)"', r'"\1\2"', text)
        text = re.sub(r'"([^"]*)\s+([^"]*)"', r'"\1 \2"', text)

        # 删除非法末尾逗号
        text = re.sub(r',(\s*[\]}])', r'\1', text)

        # 处理未闭合问题（简单补全）
        if text.count("[") > text.count("]"):
            text += "]"
        if text.count("{") > text.count("}"):
            text += "}"

        # 清理换行、空行等
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "".join(lines)

        # 最终尝试解析
        parsed = json.loads(text)

        return ServiceResponse(
            status=ServiceExecStatus.SUCCESS,
            content=parsed
        )

    except Exception as e:
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content={
                "error": f"JSON修复失败: {str(e)}",
                "raw_input": text
            }
        )


def return_result(result: Any) -> ServiceResponse:
    """
    返回最终结果
    
    Args:
        result (Any): 要返回的结果
        
    Returns:
        ServiceResponse: 包含结果的响应
    """
    return ServiceResponse(
        status=ServiceExecStatus.SUCCESS,
        content=result
    )

