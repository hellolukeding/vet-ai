import os
import sys
from pathlib import Path

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ai_diagnosis.re_diagnosis import ReDiagnosis


def test_re_diagnosis():
    """测试ReDiagnosis功能"""
    print("开始测试ReDiagnosis...")
    
    # 创建ReDiagnosis实例
    diagnosis = ReDiagnosis()
    
    # 测试用例
    test_case = "姓名凯凯，为一雌性金毛犬，现年7岁，体重26 kg。送来时主诉:最近几天精神不好，食欲不振，有浓鼻液、浓眼屎，打喷嚏，拉稀。"
    
    print(f"测试用例: {test_case}")
    print("=" * 50)
    
    # 调用诊断功能
    result = diagnosis.dialog_diagnosis(test_case)
    
    print("诊断结果:")
    print(result)
    
    if hasattr(result, 'content'):
        print(f"结果内容: {result.content}")
    
    return result

if __name__ == "__main__":
    print("开始测试ReDiagnosis")
    print("=" * 50)
    
    try:
        result = test_re_diagnosis()
        print("测试完成")
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()