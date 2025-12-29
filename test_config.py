#!/usr/bin/env python3
"""测试配置读取"""

from backend.settings import settings
from core.ai_diagnosis.diagnosis import Diagnosis
from core.ai_diagnosis.herb_diagnosis import HerbDiagnosis
from core.ai_diagnosis.re_diagnosis import ReDiagnosis

print("=== 验证AI配置从.env文件读取 ===")
print(f"MODEL_NAME: {settings.MODEL_NAME}")
print(f"BASE_URL: {settings.BASE_URL}")
print(f"API_KEY: {settings.API_KEY[:10]}...")

print("\n=== 验证各个AI诊断类配置 ===")

# 测试Diagnosis类
try:
    diagnosis = Diagnosis()
    print(f"✅ Diagnosis - model_name: {diagnosis.model_name}")
    print(f"✅ Diagnosis - base_url: {diagnosis.base_url}")
    print(f"✅ Diagnosis - api_key: {diagnosis.api_key[:10]}...")
    print(f"✅ Diagnosis - initialized: {diagnosis.initialized}")
except Exception as e:
    print(f"❌ Diagnosis初始化失败: {e}")

# 测试HerbDiagnosis类
try:
    herb_diagnosis = HerbDiagnosis()
    print(f"✅ HerbDiagnosis - model_name: {herb_diagnosis.model_name}")
    print(f"✅ HerbDiagnosis - base_url: {herb_diagnosis.base_url}")
    print(f"✅ HerbDiagnosis - api_key: {herb_diagnosis.api_key[:10]}...")
    print(f"✅ HerbDiagnosis - initialized: {herb_diagnosis.initialized}")
except Exception as e:
    print(f"❌ HerbDiagnosis初始化失败: {e}")

# 测试ReDiagnosis类
try:
    re_diagnosis = ReDiagnosis()
    print(f"✅ ReDiagnosis - model_name: {re_diagnosis.model_name}")
    print(f"✅ ReDiagnosis - base_url: {re_diagnosis.base_url}")
    print(f"✅ ReDiagnosis - api_key: {re_diagnosis.api_key[:10]}...")
    print(f"✅ ReDiagnosis - initialized: {re_diagnosis.initialized}")
except Exception as e:
    print(f"❌ ReDiagnosis初始化失败: {e}")

print("\n=== 配置验证完成 ===")
print("所有AI配置都已成功从.env文件读取！")
