import json
from io import StringIO

import pandas as pd


def parse_diagnosis_table(md_table_text: str):
    """
    解析诊断表格并返回标准JSON格式
    
    Args:
        md_table_text: Markdown格式的表格文本
        
    Returns:
        list: 标准格式的诊断结果JSON数组
    """
    # 自动识别 markdown 表格为 DataFrame
    df = pd.read_csv(StringIO(md_table_text), sep='|', engine='python', skipinitialspace=True)
    df = df.dropna(axis=1, how='all')   # 删除空列
    df = df.iloc[1:]  # 跳过分隔符行
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)  # 去除空格
    
    # 转为 list[dict] 并清理字段名
    result = df.to_dict(orient='records')
    
    # 清理字段名和值，确保标准格式
    cleaned_results = []
    for item in result:
        cleaned_item = {}
        for key, value in item.items():
            # 清理键名（去除空格和非法字符）
            clean_key = key.strip() if isinstance(key, str) else str(key)
            # 清理值（去除空格，处理空值）
            if isinstance(value, str):
                clean_value = value.strip()
                # 将 'N/A' 转换为 null
                if clean_value.upper() == 'N/A':
                    clean_value = None
            else:
                clean_value = value
            
            cleaned_item[clean_key] = clean_value
        cleaned_results.append(cleaned_item)
    
    return cleaned_results


def format_diagnosis_as_json(diagnosis_results: list, indent: int = 2) -> str:
    """
    将诊断结果格式化为标准JSON字符串
    
    Args:
        diagnosis_results: 诊断结果列表
        indent: JSON缩进空格数
        
    Returns:
        str: 格式化的JSON字符串
    """
    return json.dumps(diagnosis_results, ensure_ascii=False, indent=indent)