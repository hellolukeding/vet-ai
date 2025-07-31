import os
import sys
from pathlib import Path
import json

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ai_diagnosis.diagnosis import Diagnosis, extract_json_block, format_json_diagnosis
from agentscope.message import Msg
from agentscope.service import ServiceToolkit, ServiceResponse, ServiceExecStatus


def test_extract_json_block():
    """测试extract_json_block函数"""
    print("测试extract_json_block函数")
    print("=" * 30)
    
    # 测试正常情况
    test_text = '''这是一个测试文本
```json
[
  {
    "disease": "犬瘟热",
    "p": 0.87,
    "base": "建议静养，保持温暖",
    "continue": "使用抗病毒药物",
    "suggest": "前往医院治疗并输液"
  }
]
```
这是结束文本'''
    
    result = extract_json_block(test_text)
    print(f"正常情况测试结果: {result}")
    
    # 测试没有代码块的情况
    test_text_no_block = '''[
  {
    "disease": "犬瘟热",
    "p": 0.87,
    "base": "建议静养，保持温暖",
    "continue": "使用抗病毒药物",
    "suggest": "前往医院治疗并输液"
  }
]'''
    
    result_no_block = extract_json_block(test_text_no_block)
    print(f"无代码块测试结果: {result_no_block}")
    

def test_format_json_diagnosis():
    """测试format_json_diagnosis函数"""
    print("\n测试format_json_diagnosis函数")
    print("=" * 30)
    
    # 测试正常JSON
    normal_json = '''[
  {
    "disease": "犬瘟热",
    "p": 0.87,
    "base": "建议静养，保持温暖",
    "continue": "使用抗病毒药物",
    "suggest": "前往医院治疗并输液"
  }
]'''
    
    result = format_json_diagnosis(normal_json)
    print(f"正常JSON测试结果: {result}")
    
    # 测试包含中文引号的JSON
    chinese_quote_json = '''[
  {
    "disease": "犬瘟热",
    "p": 0.87,
    "base": "建议静养，保持温暖",
    "continue": "使用抗病毒药物",
    "suggest": "前往医院治疗并输液"
  }
]'''
    
    result_chinese = format_json_diagnosis(chinese_quote_json)
    print(f"中文引号JSON测试结果: {result_chinese}")


def test_full_workflow():
    """测试完整的工作流程"""
    print("\n测试完整工作流程")
    print("=" * 30)
    
    # 创建诊断实例
    diagnosis = Diagnosis()
    
    # 测试案例描述
    description = "姓名凯凯，为一雌性金毛犬，:现年7岁，体重26 kg。送来时主诉:最近几天精神不好，食欲不振，有浓鼻液、浓眼屎，打喷嚏，拉稀。"
    
    print(f"测试描述: {description}")
    
    # 调用dialog_diagnosis方法
    result = diagnosis.dialog_diagnosis(description)
    
    print(f"诊断结果: {result}")
    print(f"结果类型: {type(result)}")
    print(f"结果长度: {len(result)}")
    
    if isinstance(result, list) and len(result) > 0:
        print("诊断成功，返回了结果:")
        for i, item in enumerate(result):
            print(f"  诊断项 {i+1}: {item}")
    else:
        print("诊断失败或未返回结果")


if __name__ == "__main__":
    print("开始测试诊断工作流程")
    print("=" * 50)
    
    try:
        test_extract_json_block()
        test_format_json_diagnosis()
        test_full_workflow()
        print("\n所有测试完成")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()