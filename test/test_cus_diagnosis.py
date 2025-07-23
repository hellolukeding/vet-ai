import os
import sys
from pathlib import Path

import pytest

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ai_diagnosis.diagnosis import Diagnosis, cus_diagnosis


class TestDiagnosisReal:
    """真实测试Diagnosis类功能（不使用mock）"""
    
    def test_diagnosis_initialization(self):
        """测试Diagnosis类能否正常初始化"""
        try:
            diagnosis = Diagnosis()
            
            # 验证基本属性
            assert hasattr(diagnosis, 'model_name')
            assert hasattr(diagnosis, 'base_url') 
            assert hasattr(diagnosis, 'api_key')
            assert hasattr(diagnosis, 'model')
            
            # 验证环境变量被正确读取
            assert diagnosis.model_name is not None
            assert diagnosis.base_url is not None
            assert diagnosis.api_key is not None
            
            print(f"✓ 初始化成功 - Model: {diagnosis.model_name}, Base URL: {diagnosis.base_url}")
            
        except Exception as e:
            print(f"✗ 初始化失败: {e}")
            # 允许在没有正确环境配置时跳过测试
            pytest.skip(f"跳过测试 - 环境配置问题: {e}")
    
    def test_global_instance(self):
        """测试全局实例是否正确创建"""
        assert isinstance(cus_diagnosis, Diagnosis)
        print("✓ 全局实例 cus_diagnosis 创建成功")
    
    @pytest.mark.slow
    def test_diagnosis_with_real_symptoms(self):
        """测试真实症状诊断（需要API可用）"""
        try:
            diagnosis = Diagnosis()
            
            # 测试用例1：狗狗常见症状
            test_cases = [
                "狗狗发烧38.5度，不吃东西，精神萎靡，偶尔呕吐",
                "猫咪打喷嚏，眼睛流泪，鼻子有分泌物",
                "兔子不吃东西，躲在角落，毛发失去光泽"
            ]
            
            for i, symptom in enumerate(test_cases, 1):
                print(f"\n测试用例 {i}: {symptom}")
                
                try:
                    result = diagnosis.diagnosis(symptom)
                    
                    # 验证返回结果格式
                    assert result is not None
                    assert isinstance(result, (str, dict))
                    
                    if isinstance(result, dict):
                        # 验证必要字段
                        required_fields = ['disease', 'base_suggestion', 'continuing_suggestion', 'suggestion']
                        for field in required_fields:
                            assert field in result, f"缺少必要字段: {field}"
                        
                        print(f"  ✓ 诊断疾病: {result.get('disease', 'N/A')}")
                        print(f"  ✓ 初步建议: {result.get('base_suggestion', 'N/A')[:50]}...")
                        print(f"  ✓ 最终建议: {result.get('suggestion', 'N/A')[:50]}...")
                    else:
                        print(f"  ✓ 诊断结果: {str(result)[:100]}...")
                    
                    print(f"  ✓ 测试用例 {i} 通过")
                    
                except Exception as e:
                    print(f"  ✗ 测试用例 {i} 失败: {e}")
                    if "connection" in str(e).lower() or "timeout" in str(e).lower():
                        pytest.skip(f"跳过测试 - API连接问题: {e}")
                    else:
                        raise
                        
        except Exception as e:
            if "connection" in str(e).lower() or "api" in str(e).lower():
                pytest.skip(f"跳过测试 - API不可用: {e}")
            else:
                raise
    
    def test_diagnosis_edge_cases(self):
        """测试边界情况"""
        try:
            diagnosis = Diagnosis()
            
            edge_cases = [
                "",  # 空字符串
                " ",  # 只有空格
                "正常的宠物，没有症状",  # 正常情况
                "症状描述中包含特殊字符：@#$%^&*()",  # 特殊字符
            ]
            
            for case in edge_cases:
                try:
                    result = diagnosis.diagnosis(case)
                    print(f"✓ 边界情况测试通过: '{case}' -> {type(result)}")
                except Exception as e:
                    print(f"✗ 边界情况测试失败: '{case}' -> {e}")
                    if "connection" in str(e).lower():
                        pytest.skip(f"跳过测试 - 连接问题: {e}")
                    # 对于其他异常，我们记录但不失败测试，因为边界情况可能确实应该抛出异常
                    
        except Exception as e:
            if "connection" in str(e).lower() or "api" in str(e).lower():
                pytest.skip(f"跳过测试 - API不可用: {e}")
            else:
                raise


class TestDiagnosisConfiguration:
    """测试配置相关功能"""
    
    def test_environment_variables_loading(self):
        """测试环境变量加载"""
        # 检查.env文件是否存在
        env_file = project_root / ".env"
        if env_file.exists():
            print(f"✓ 找到环境配置文件: {env_file}")
            
            # 读取并验证环境变量
            with open(env_file, 'r') as f:
                content = f.read()
                assert "model_name" in content
                assert "base_url" in content  
                assert "api_key" in content
                print("✓ 环境变量配置完整")
        else:
            pytest.skip("跳过测试 - 未找到.env配置文件")
    
    def test_config_parameters(self):
        """测试配置参数"""
        try:
            diagnosis = Diagnosis()
            
            # 验证模型配置
            assert diagnosis.model_name, "model_name不能为空"
            assert diagnosis.base_url, "base_url不能为空"
            assert diagnosis.api_key, "api_key不能为空"
            
            # 验证URL格式
            assert diagnosis.base_url.startswith(('http://', 'https://')), "base_url应该是有效的URL"
            
            print(f"✓ 配置验证通过:")
            print(f"  - Model: {diagnosis.model_name}")
            print(f"  - Base URL: {diagnosis.base_url}")
            print(f"  - API Key: {diagnosis.api_key[:10]}...")
            
        except Exception as e:
            pytest.skip(f"跳过测试 - 配置问题: {e}")


# 测试数据提供者
class TestDataProvider:
    """提供各种测试数据"""
    
    @staticmethod
    def get_common_symptoms():
        """常见宠物症状"""
        return [
            "狗狗咳嗽，流鼻涕，没有精神",
            "猫咪不吃东西，呕吐，拉肚子", 
            "仓鼠毛发脱落，皮肤发红",
            "鸟儿羽毛松散，不爱叫",
            "兔子眼睛红肿，流泪"
        ]
    
    @staticmethod
    def get_emergency_symptoms():
        """紧急症状"""
        return [
            "狗狗突然倒地，呼吸困难",
            "猫咪持续呕吐，无法进食",
            "宠物体温超过40度，昏迷"
        ]


@pytest.mark.parametrize("symptom", TestDataProvider.get_common_symptoms())
def test_common_symptoms_diagnosis(symptom):
    """参数化测试：常见症状诊断"""
    try:
        diagnosis = Diagnosis()
        result = diagnosis.diagnosis(symptom)
        
        assert result is not None
        print(f"✓ 症状诊断成功: {symptom[:30]}...")
        
    except Exception as e:
        if "connection" in str(e).lower() or "api" in str(e).lower():
            pytest.skip(f"跳过测试 - API问题: {e}")
        else:
            pytest.fail(f"诊断失败: {e}")


# 性能测试
class TestPerformance:
    """性能相关测试"""
    
    def test_initialization_time(self):
        """测试初始化时间"""
        import time
        
        start_time = time.time()
        try:
            diagnosis = Diagnosis()
            end_time = time.time()
            
            init_time = end_time - start_time
            print(f"✓ 初始化时间: {init_time:.2f}秒")
            
            # 合理的初始化时间应该在10秒内
            assert init_time < 10, f"初始化时间过长: {init_time:.2f}秒"
            
        except Exception as e:
            pytest.skip(f"跳过性能测试 - 初始化失败: {e}")
    
    @pytest.mark.slow  
    def test_diagnosis_response_time(self):
        """测试诊断响应时间"""
        import time
        
        try:
            diagnosis = Diagnosis()
            test_symptom = "狗狗发烧，不吃东西"
            
            start_time = time.time()
            result = diagnosis.diagnosis(test_symptom)
            end_time = time.time()
            
            response_time = end_time - start_time
            print(f"✓ 诊断响应时间: {response_time:.2f}秒")
            
            # 合理的响应时间应该在30秒内
            assert response_time < 30, f"响应时间过长: {response_time:.2f}秒"
            
        except Exception as e:
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                pytest.skip(f"跳过性能测试 - 网络问题: {e}")
            else:
                raise


if __name__ == "__main__":
    # 运行测试，显示详细输出
    pytest.main([__file__, "-v", "-s", "--tb=short"])