import os
import sys
from pathlib import Path
import json

import pytest

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ai_diagnosis.diagnosis import Diagnosis


class TestDialogDiagnosis:
    """测试Diagnosis类的dialog_diagnosis方法"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.diagnosis = Diagnosis()
        
    def test_dialog_diagnosis_with_sample_case(self):
        """测试指定的测试案例"""
        # 测试案例描述
        description = "姓名凯凯，为一雌性金毛犬，:现年7岁，体重26 kg。送来时主诉:最近几天精神不好，食欲不振，有浓鼻液、浓眼屎，打喷嚏，拉稀。"
        
        # 调用dialog_diagnosis方法
        result = self.diagnosis.dialog_diagnosis(description)
        
        # 验证结果
        assert result is not None, "诊断结果不应为None"
        assert isinstance(result, list), f"诊断结果应为列表，实际类型为: {type(result)}"
        
        # 如果有诊断结果，验证格式
        if len(result) > 0:
            for i, item in enumerate(result):
                assert isinstance(item, dict), f"第{i}个诊断项应为字典，实际类型为: {type(item)}"
                
                # 验证必需字段
                required_fields = ["disease", "p", "base", "continue", "suggest"]
                for field in required_fields:
                    assert field in item, f"第{i}个诊断项缺少必需字段: {field}"
                    assert item[field] is not None, f"第{i}个诊断项的字段{field}不应为None"
                    
                # 验证置信度范围
                assert isinstance(item["p"], (int, float)), f"第{i}个诊断项的置信度应为数值类型"
                assert 0 <= item["p"] <= 1, f"第{i}个诊断项的置信度应在0-1之间，实际值为: {item['p']}"
                
                # 验证字段类型
                assert isinstance(item["disease"], str), f"第{i}个诊断项的疾病名称应为字符串"
                assert isinstance(item["base"], str), f"第{i}个诊断项的初步建议应为字符串"
                assert isinstance(item["continue"], str), f"第{i}个诊断项的持续建议应为字符串"
                assert isinstance(item["suggest"], str), f"第{i}个诊断项的重度建议应为字符串"
                
        print(f"诊断结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
    def test_dialog_diagnosis_with_empty_description(self):
        """测试空描述"""
        description = ""
        result = self.diagnosis.dialog_diagnosis(description)
        assert isinstance(result, list), "诊断结果应为列表"
        # 空描述应返回空列表或默认结果
        assert len(result) >= 0, "诊断结果列表长度应大于等于0"
        
    def test_dialog_diagnosis_with_none_description(self):
        """测试None描述"""
        description = None
        result = self.diagnosis.dialog_diagnosis(description)
        assert isinstance(result, list), "诊断结果应为列表"
        assert len(result) == 0, "None描述应返回空列表"


if __name__ == "__main__":
    # 运行测试
    test_instance = TestDialogDiagnosis()
    test_instance.setup_method()
    
    print("开始测试指定案例...")
    try:
        test_instance.test_dialog_diagnosis_with_sample_case()
        print("✓ 指定案例测试通过")
    except Exception as e:
        print(f"✗ 指定案例测试失败: {e}")
        
    print("开始测试空描述...")
    try:
        test_instance.test_dialog_diagnosis_with_empty_description()
        print("✓ 空描述测试通过")
    except Exception as e:
        print(f"✗ 空描述测试失败: {e}")
        
    print("开始测试None描述...")
    try:
        test_instance.test_dialog_diagnosis_with_none_description()
        print("✓ None描述测试通过")
    except Exception as e:
        print(f"✗ None描述测试失败: {e}")
        
    print("所有测试完成")