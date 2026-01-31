"""
工具函数：从Markdown代码块中提取JSON内容
"""

import json
import re
from typing import Any, Dict, List, Union


def extract_json_from_markdown(text: str) -> str:
    """
    从Markdown代码块中提取JSON内容

    Args:
        text (str): 包含Markdown代码块的文本

    Returns:
        str: 提取出的纯JSON字符串
    """
    # 匹配```json ... ```或``` ... ```格式的代码块
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return text


def parse_markdown_json(text: str) -> Union[Dict[str, Any], List[Any], None]:
    """
    从包含Markdown代码块的文本中提取并解析JSON

    Args:
        text (str): 包含Markdown代码块的文本

    Returns:
        Union[Dict[str, Any], List[Any], None]: 解析后的JSON对象，如果解析失败则返回None
    """
    # 首先提取JSON文本
    json_text = extract_json_from_markdown(text)

    # 尝试解析JSON
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        # 如果直接解析失败，可以在这里添加额外的修复逻辑
        # 比如调用fix_broken_json等函数
        pass

    return None


__all__ = ["extract_json_from_markdown", "parse_markdown_json"]
