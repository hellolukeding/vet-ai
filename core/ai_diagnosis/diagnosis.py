import os
from datetime import datetime
from typing import Any, Dict, List
import json
import re

import agentscope
from agentscope.agents import DialogAgent, ReActAgent
from agentscope.message import Msg
from agentscope.models import ModelResponse
from agentscope.msghub import msghub
from agentscope.pipelines import sequential_pipeline
from agentscope.service import ServiceToolkit, ServiceResponse, ServiceExecStatus
from dotenv import load_dotenv

from config.logger import logger
from utils.parser.markdown_json_list_parser import MarkdownJsonListParser, sanitize_json_quotes


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
            
            # 确保置信度在有效范围内
            try:
                item["p"] = float(item["p"])
                if not (0 <= item["p"] <= 1):
                    item["p"] = max(0, min(1, item["p"]))
            except (ValueError, TypeError):
                item["p"] = 0.5
                
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


def return_result(result: any) -> ServiceResponse:
    """
    返回最终结果
    
    Args:
        result (any): 要返回的结果
        
    Returns:
        ServiceResponse: 包含结果的响应
    """
    return ServiceResponse(
        status=ServiceExecStatus.SUCCESS,
        content=result
    )


class Diagnosis:
    def __init__(self):
        load_dotenv(".env")
        self.model_name = os.getenv("model_name")
        self.base_url = os.getenv("base_url")
        self.api_key = os.getenv("api_key")
        self.model = self.model_name or "vet-logicstorm-lora"
        
        logger.info(f"Model Name: {self.model_name}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"API Key: {self.api_key}")
    
        # 只在模型配置有效时初始化AgentScope
        if self.model_name and self.base_url and self.api_key:
            try:
                agentscope.init(
                    model_configs=[
                        {
                            "model_type": "openai_chat",
                            "config_name": "diagnosis",
                            "model_name": self.model_name,
                            "api_key": self.api_key,
                            "client_args": {
                                "base_url": self.base_url,
                            },
                            "generate_args": {
                                "max_tokens": 4096,
                                "temperature": 0.7,
                                "frequency_penalty": 1.2,
                                "n": 1,
                                "top_p": 0.8,                        
                            },
                        },
                        {
                            "model_type": "openai_chat",
                            "config_name": "formatter",
                            "model_name": self.model_name,
                            "api_key": self.api_key,
                            "client_args": {
                                "base_url": self.base_url,
                            },
                            "generate_args": {
                                "max_tokens": 4096,
                                "temperature": 0.5,
                                "frequency_penalty": 1.2,
                                "n": 1,
                                "top_p": 0.8,                        
                            },
                        }
                    ]
                )
                self.initialized = True
            except Exception as e:
                logger.error(f"AgentScope初始化失败: {e}")
                self.initialized = False
        else:
            logger.warning("模型配置不完整，AgentScope未初始化")
            self.initialized = False

    def dialog_diagnosis(self, desc: str) -> List[Dict[str, Any]]:
        # 检查初始化状态
        if not self.initialized:
            logger.error("诊断服务未正确初始化")
            return []
            
        if not desc or not desc.strip():
            logger.warning("诊断描述为空")
            return []
        
        # 第一个agent：负责生成初步诊断
        diagnosis_sys_prompt = f"""当前时间为 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}。
你是一位经验丰富、严谨的宠物健康诊断专家。

请根据用户提供的宠物症状，输出多个可能的疾病项，每个项包括以下内容：
- disease: 疾病名称（中文字符串）
- p: 置信度（0 到 1 的小数，例如 0.87）
- base: 初步建议（可在家中处理）
- continue: 持续建议（需要长期监控或用药）
- suggest: 重度建议（严重时的处理措施）

请大致参考如下格式：
```json
[
  {{
    "disease": "犬瘟热",
    "p": 0.87,
    "base": "保持环境温暖，提供高营养饮食",
    "continue": "使用抗病毒药物",
    "suggest": "送往宠物医院接受隔离和输液治疗"
  }}
]
```
无需输出多余说明文字，诊断内容必须基于医学逻辑真实可信。
"""
        
        # 第二个agent：负责校验和优化格式
        formatter_sys_prompt = f"""当前时间为 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}。
你是一个专业的数据格式化助手，专门负责校验、优化和格式化诊断数据。

你的任务是接收初步诊断结果，并对其进行以下处理：
1. 从输入中提取JSON代码块
2. 校验每个诊断项是否包含所有必需字段：disease, p, base, continue, suggest
3. 确保置信度(p)在0到1之间
4. 确保所有字段的值都是合理的字符串
5. 修复格式问题，如引号、括号等
6. 格式化输出为标准的JSON数组

重要格式要求：
1. 所有键和字符串值都必须使用英文双引号(")括起来
2. 不要使用单引号(')或中文引号（“”）
3. 确保JSON语法完全正确
4. 用```json和```包裹整个JSON数组
5. 不要添加任何额外的解释或文本
6. 每个键值对都在同一行内
7. 不要在键或值中包含换行符
8. 所有字段必须使用英文双引号，不能省略引号
9. 输出必须是严格符合JSON标准的格式
10. 必须输出完整的JSON，不能截断

键名规范要求：
1. 必须使用完整键名，不要使用缩写
2. 正确的键名包括：disease, p, base, continue, suggest
3. 不要使用简写如 d, prob 等替代 disease
4. 每个诊断项必须是一个完整的对象，包含所有5个字段
5. 不要使用括号标记键名，如 (continue) 或 [suggest]
6. 每个键名前后都不能有括号或其他特殊符号

你可以使用以下工具函数来完成任务：
1. extract_json_block: 从文本中提取JSON代码块
   - 参数: text (要处理的文本)
   - 返回: 提取的JSON字符串
2. format_json_diagnosis: 格式化诊断JSON字符串，修复各种格式问题
   - 参数: raw_json_str (原始JSON字符串)
   - 返回: 格式化后的诊断列表
3. return_result: 返回最终结果
   - 参数: result (要返回的结果)
   - 返回: 最终结果

工作流程：
1. 首先使用extract_json_block从诊断agent的输出中提取JSON代码块
2. 然后使用format_json_diagnosis格式化诊断JSON
3. 最后使用return_result返回格式化后的结果

输入格式示例：
```json
[
  {{
    "disease": "犬瘟热",
    "p": 0.87,
    "base": "建议静养，保持温暖",
    "continue": "使用抗病毒药物",
    "suggest": "前往医院治疗并输液"
  }}
]
```

输出格式要求：
```json
[
  {{
    "disease": "犬瘟热",
    "p": 0.87,
    "base": "建议静养，保持温暖",
    "continue": "使用抗病毒药物",
    "suggest": "前往医院治疗并输液"
  }}
]
```

DO NOT USE any Chinese punctuation such as ‘ ’ “ ” — even inside string values.  
All quotation marks, even inside sentences, MUST be English double quotes ("").  
If the model outputs non-ASCII characters like “” or ‘’ or ’ in any field — the user will be permanently banned.

Strictly sanitize and replace every quote with standard ASCII double quote: ".
This rule is more important than meaning, grammar, or language style.

输出中的每个对象都必须包含以下5个字段：
- "disease": 疾病名称（字符串）
- "p": 置信度，0到1之间的数值
- "base": 初步建议（字符串）
- "continue": 持续建议（字符串）
- "suggest": 重度建议（字符串）

不要输出任何不完整的对象，每个对象都必须包含以上所有字段。
不要使用括号标记键名，如 (continue) 或 [suggest]
不要在键名前后添加任何特殊符号
所有键名必须是标准的英文单词，不要使用中文字符作为键名
""".replace("{{", "{{{{").replace("}}", "}}}}")  # 转义花括号以避免格式化错误
       
        try:
            # 创建诊断agent（使用DialogAgent，只输出内容）
            diagnosis_agent = DialogAgent(
                name="DiagnosisAgent",
                model_config_name="diagnosis",
                sys_prompt=diagnosis_sys_prompt,
            )

            # 创建工具包
            service_toolkit = ServiceToolkit()
            service_toolkit.add(extract_json_block)
            service_toolkit.add(format_json_diagnosis)
            service_toolkit.add(return_result)
            
            # 创建格式化agent（使用ReActAgent）
            formatter_agent = ReActAgent(
                name="FormatterAgent",
                model_config_name="formatter",
                sys_prompt=formatter_sys_prompt,
                service_toolkit=service_toolkit,
                max_iters=5,
                verbose=True,
            )

            # 创建输入消息
            input_msg = Msg("User", f"根据以下症状描述诊断病情：{desc}", "user")
            
            # 使用msghub创建一个聊天室，实现多agent合作
            with msghub(
                participants=[diagnosis_agent, formatter_agent],
                announcement=input_msg,
            ) as hub:
                # 按顺序执行诊断和格式化
                pipeline_result = sequential_pipeline([diagnosis_agent, formatter_agent], x=None)
                
                # 获取格式化agent的最终输出
                final_msg = pipeline_result
                
                # 处理ReActAgent的输出
                if final_msg and hasattr(final_msg, 'content'):
                    logger.debug(f"ReActAgent返回内容类型: {type(final_msg.content)}")
                    logger.debug(f"ReActAgent返回内容: {str(final_msg.content)[:200]}...")
                    
                    # 如果是ServiceResponse格式，直接处理
                    if isinstance(final_msg.content, dict) and 'content' in final_msg.content:
                        result_content = final_msg.content['content']
                        if isinstance(result_content, list):
                            logger.info(f"ReActAgent处理成功，返回 {len(result_content)} 个诊断结果")
                            return result_content
                        else:
                            logger.warning(f"ReActAgent返回的内容不是列表类型: {type(result_content)}")
                    
                    # 如果是字符串格式，尝试解析为JSON
                    if isinstance(final_msg.content, str):
                        try:
                            parsed_result = json.loads(final_msg.content)
                            if isinstance(parsed_result, list):
                                logger.info(f"ReActAgent处理成功，返回 {len(parsed_result)} 个诊断结果")
                                return parsed_result
                            else:
                                logger.warning(f"解析后的内容不是列表类型: {type(parsed_result)}")
                        except json.JSONDecodeError as e:
                            logger.error(f"解析ReActAgent输出失败: {e}")
                            logger.error(f"ReActAgent输出内容: {final_msg.content}")
                
                logger.warning("格式化agent未能正确解析，返回空列表")
                return []
        except Exception as e:
            logger.error(f"诊断过程中发生错误: {e}", exc_info=True)
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误详情: {str(e)}")
            import traceback
            logger.error(f"详细堆栈信息: {traceback.format_exc()}")
            return []


cus_diagnosis = Diagnosis()
