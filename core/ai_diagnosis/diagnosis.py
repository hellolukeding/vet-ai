import os
import re
from typing import Any, Dict, List

import agentscope
from agentscope.agents import DialogAgent
from agentscope.message import Msg
from dotenv import load_dotenv

from config.logger import logger


def extract_table_only(text: str) -> str:
    """从文本中提取第一个 Markdown 表格块"""
    pattern = r"(\|.+\|(?:\n\|[-\s|]+\|)?(?:\n\|.*\|)+)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else text


def parse_diagnosis_table(table_str: str) -> List[Dict[str, str]]:
    """
    解析Markdown表格，自动补齐缺失列，避免因列数不匹配导致丢失整行
    """
    lines = [line.strip() for line in table_str.strip().split('\n') if line.strip()]
    if len(lines) < 3:
        return []

    headers = [h.strip() for h in lines[0].strip('|').split('|')]
    expected_col_count = len(headers)

    results = []

    for line in lines[2:]:  # 跳过分隔线
        cols = [c.strip() for c in line.strip('|').split('|')]
        if len(cols) < expected_col_count:
            # 补齐缺失列
            cols += [''] * (expected_col_count - len(cols))
            logger.warning(f"发现列数不足，自动补齐：{cols}")
        if len(cols) != expected_col_count:
            logger.warning(f"跳过异常行，列数不匹配：{line}")
            continue
        results.append(dict(zip(headers, cols)))

    return results


def parse_probability(p_value: str) -> float:
    """
    尝试从字符串中提取概率值，如果无法解析则返回默认值
    """
    if not p_value:
        return 0.0
    
    # 移除空格和常见的中文字符
    p_clean = p_value.strip()
    
    # 尝试直接转换为浮点数
    try:
        return float(p_clean)
    except ValueError:
        pass
    
    # 尝试提取数字（支持百分比）
    import re
    number_pattern = r'(\d+(?:\.\d+)?)'
    matches = re.findall(number_pattern, p_clean)
    
    if matches:
        try:
            num = float(matches[0])
            # 如果包含%符号，转换为小数
            if '%' in p_clean:
                return num / 100.0
            # 如果数字大于1，可能是百分比格式
            elif num > 1:
                return num / 100.0
            else:
                return num
        except ValueError:
            pass
    
    # 根据关键词给出默认概率值
    if any(keyword in p_clean for keyword in ['良好', '优', '高']):
        return 0.8
    elif any(keyword in p_clean for keyword in ['一般', '中等', '谨慎']):
        return 0.6
    elif any(keyword in p_clean for keyword in ['差', '低', '严重', '危险']):
        return 0.3
    
    logger.warning(f"无法解析概率值: {p_value}，使用默认值 0.5")
    return 0.5


def format_json_diagnosis(parsed: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    result = []
    for row in parsed:
        try:
            p_value = row.get("p", "0.0")
            probability = parse_probability(p_value)
            
            result.append({
                "disease": row.get("disease", ""),
                "description": row.get("description", ""),
                "p": probability,
                "base": row.get("base", ""),
                "continue": row.get("continue", ""),
                "suggest": row.get("suggest", ""),
                "base_medicine": row.get("base_medicine", ""),
                "base_medicine_usage": row.get("base_medicine_usage", ""),
                "continue_medicine": row.get("continue_medicine", ""),
                "continue_medicine_usage": row.get("continue_medicine_usage", ""),
                "suggest_medicine": row.get("suggest_medicine", ""),
                "suggest_medicine_usage": row.get("suggest_medicine_usage", ""),
            })
            logger.info(f"成功格式化诊断: {row.get('disease', 'Unknown')} - 概率: {probability}")
        except Exception as e:
            logger.warning(f"格式化单行失败: {e}, 行数据: {row}")
            # 即使格式化失败，也尝试保留基本信息
            result.append({
                "disease": row.get("disease", ""),
                "description": row.get("description", ""),
                "p": 0.5,  # 默认概率
                "base": row.get("base", ""),
                "continue": row.get("continue", ""),
                "suggest": row.get("suggest", ""),
                "base_medicine": row.get("base_medicine", ""),
                "base_medicine_usage": row.get("base_medicine_usage", ""),
                "continue_medicine": row.get("continue_medicine", ""),
                "continue_medicine_usage": row.get("continue_medicine_usage", ""),
                "suggest_medicine": row.get("suggest_medicine", ""),
                "suggest_medicine_usage": row.get("suggest_medicine_usage", ""),
            })
    return result


class Diagnosis:
    def __init__(self):
        load_dotenv(".env")
        self.model_name = os.getenv("model_name")
        self.base_url = os.getenv("base_url")
        self.api_key = os.getenv("api_key")
        self.sys_prompt = None
        self.initialized = False
        self.agent: DialogAgent = None

        logger.info(f"Model Name: {self.model_name}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"API Key: {self.api_key}")

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
                                "max_tokens": 1024,
                                "temperature": 0.7,
                                "top_p": 0.8,
                            },
                        },
                    ]
                )
                self.initialized = True
                self._init_prompt()
                self._init_agent()
            except Exception as e:
                logger.error(f"AgentScope 初始化失败: {e}")
        else:
            logger.warning("模型配置不完整，AgentScope 未初始化")

    def _init_prompt(self) -> None:
        self.sys_prompt = """你是执业兽医，请根据以下症状严格输出包含13列的Markdown表格诊断结果，不得缺失列，尤其是最后一列不能截断：

| disease | description | p | base | continue | suggest | base_medicine | base_medicine_usage | continue_medicine | continue_medicine_usage | suggest_medicine | suggest_medicine_usage |
|---------|-------------|---|------|----------|---------|---------------|---------------------|-------------------|-------------------------|------------------|------------------------|

所有字段必须完整输出，不得多余文字。请开始诊断："""

    def _init_agent(self) -> None:
        self.agent = DialogAgent(
            name="diagnosis",
            model_config_name="diagnosis",
            sys_prompt=self.sys_prompt,
        )

    def diagnosis(self, desc: str) -> List[Dict[str, Any]]:
        if not self.initialized or self.agent is None:
            logger.error("诊断模型未初始化")
            return []

        user_message = f"""症状描述：{desc}

请严格输出符合要求的表格格式，字段齐全，不得缺失。"""

        task = Msg("User", user_message, "user")
        result = self.agent(task)
        logger.info(f"Raw Result: {result.content}")

        cleaned_content = result.content
        logger.info(f"Cleaned Result: {cleaned_content}")

        try:
            parsed = parse_diagnosis_table(cleaned_content)
            logger.info(f"Parsed Result: {parsed}")
            return format_json_diagnosis(parsed)
        except Exception as e:
            logger.error(f"诊断解析失败: {e}")
            return []