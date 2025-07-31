import sys
from pathlib import Path
import json

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.parser.markdown_json_list_parser import clean_json_string, sanitize_json_quotes


def test_json_parsing():
    """测试JSON解析问题"""
    # 模拟从extract_json_block返回的字符串
    test_input = '[\n  {\n    "disease": "犬瘟热",\n    "p": 0.87,\n    "base": "建议静养，保持温暖",\n    "continue": "使用抗病毒药物",\n    "suggest": "前往医院治疗并输液"\n  }\n]\n'
    
    print("原始输入:")
    print(repr(test_input))
    print()
    
    # 测试clean_json_string函数
    print("测试clean_json_string函数:")
    cleaned = clean_json_string(test_input)
    print("清洗后:")
    print(repr(cleaned))
    print()
    
    # 测试直接解析
    print("直接解析原始输入:")
    try:
        parsed = json.loads(test_input)
        print("解析成功:", parsed)
    except json.JSONDecodeError as e:
        print("解析失败:", e)
    print()
    
    # 测试解析清洗后的字符串
    print("解析清洗后的字符串:")
    try:
        parsed = json.loads(cleaned)
        print("解析成功:", parsed)
    except json.JSONDecodeError as e:
        print("解析失败:", e)
    print()
    
    # 测试去除外层引号后再解析
    print("测试去除外层引号:")
    if test_input.startswith("'") and test_input.endswith("'"):
        unquoted = test_input[1:-1]
        print("去除引号后:", repr(unquoted))
        try:
            parsed = json.loads(unquoted)
            print("解析成功:", parsed)
        except json.JSONDecodeError as e:
            print("解析失败:", e)
    else:
        print("输入没有被引号包裹")


def test_problematic_string():
    """测试有问题的字符串"""
    # 从日志中看到的有问题的字符串
    problematic = '[\\n  {\\n    "disease": "犬瘟热",\\n    "p": 0.87,\\n    "base": "建议静养,保持温暖",\\n    "continue": "使用抗病毒药物",\\n    "suggest": "前往医院治疗并输液"\\n  }\\n]'
    
    print("有问题的字符串:")
    print(repr(problematic))
    print()
    
    # 尝试解析
    try:
        parsed = json.loads(problematic)
        print("解析成功:", parsed)
    except json.JSONDecodeError as e:
        print("解析失败:", e)
        print()
        
        # 尝试修复
        print("尝试修复字符串:")
        fixed = problematic.replace('\\n', '\n')
        print("修复后:", repr(fixed))
        
        try:
            parsed = json.loads(fixed)
            print("修复后解析成功:", parsed)
        except json.JSONDecodeError as e:
            print("修复后仍然解析失败:", e)


if __name__ == "__main__":
    print("开始调试JSON解析问题")
    print("=" * 50)
    test_json_parsing()
    print("\n" + "=" * 50)
    test_problematic_string()