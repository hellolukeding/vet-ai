import os
import sys
from pathlib import Path
import json

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ai_diagnosis.diagnosis import Diagnosis


def test_dialog_diagnosis():
    """测试指定的测试案例"""
    # 创建诊断实例
    diagnosis = Diagnosis()
    
    # 测试案例描述
    description = "姓名凯凯，为一雌性金毛犬，:现年7岁，体重26 kg。送来时主诉:最近几天精神不好，食欲不振，有浓鼻液、浓眼屎，打喷嚏，拉稀。"
    
    print(f"测试描述: {description}")
    print("=" * 50)
    
    # 调用dialog_diagnosis方法
    print("开始调用dialog_diagnosis方法...")
    result = diagnosis.dialog_diagnosis(description)
    
    print(f"诊断完成，结果类型: {type(result)}")
    print(f"诊断结果长度: {len(result)}")
    print(f"诊断结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 验证结果
    if result is not None and isinstance(result, list):
        print("✓ 诊断结果类型正确")
        if len(result) > 0:
            print(f"✓ 返回了{len(result)}个诊断项")
            for i, item in enumerate(result):
                print(f"  诊断项 {i+1}:")
                if isinstance(item, dict):
                    print(f"    疾病: {item.get('disease', 'N/A')}")
                    print(f"    置信度: {item.get('p', 'N/A')}")
                    print(f"    初步建议: {item.get('base', 'N/A')}")
                    print(f"    持续建议: {item.get('continue', 'N/A')}")
                    print(f"    重度建议: {item.get('suggest', 'N/A')}")
                else:
                    print(f"    错误: 诊断项 {i+1} 不是字典类型，而是 {type(item)}")
        else:
            print("⚠ 诊断结果为空列表")
    else:
        print("✗ 诊断结果类型错误或为None")
        
    return result


def test_simple_description():
    """测试一个简单的描述"""
    # 创建诊断实例
    diagnosis = Diagnosis()
    
    # 简单测试案例描述
    description = "狗狗精神不好，食欲不振"
    
    print(f"\n简单测试描述: {description}")
    print("=" * 50)
    
    # 调用dialog_diagnosis方法
    print("开始调用dialog_diagnosis方法...")
    result = diagnosis.dialog_diagnosis(description)
    
    print(f"诊断完成，结果类型: {type(result)}")
    print(f"诊断结果长度: {len(result)}")
    print(f"诊断结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    return result


if __name__ == "__main__":
    print("开始调试Diagnosis类的dialog_diagnosis方法")
    print("=" * 60)
    
    # 测试指定案例
    result1 = test_dialog_diagnosis()
    
    # 测试简单案例
    result2 = test_simple_description()
    
    print("\n" + "=" * 60)
    print("调试完成")