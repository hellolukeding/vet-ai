#!/usr/bin/env python3
"""
测试中医诊断功能
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json

from core.ai_diagnosis.herb_diagnosis import (HerbDiagnosis,
                                              format_json_herb_diagnosis,
                                              parse_probability)


def test_probability_parsing():
    """测试概率解析功能"""
    print("=== 测试概率解析功能 ===")
    test_cases = [
        "0.75",
        "0.68", 
        "75%",
        "68%",
        "谨慎，取决于病情严重程度",
        "良好",
        "一般",
        "差",
        "",
        "未知"
    ]
    
    for case in test_cases:
        result = parse_probability(case)
        print(f"输入: '{case}' -> 输出: {result}")

def test_herb_diagnosis_formatting():
    """测试中医诊断格式化"""
    print("\n=== 测试中医诊断格式化功能 ===")
    
    sample_data = [
        {
            "zhengming": "脾胃虚弱夹湿",
            "description": "基于食欲不振、精神萎靡、大便稀溏等症状，结合宠物体质判断为脾胃运化功能失调，湿邪内生，中焦气机不畅",
            "p": "0.75",
            "therapy": "健脾益气，燥湿和胃，调理中焦气机",
            "base": "饮食清淡易消化，少食多餐，保持环境温暖干燥，适当运动",
            "continue": "观察食欲变化和大便性状，监测精神状态，腹部保暖",
            "suggest": "持续呕吐腹泻脱水或高热不退应立即配合西医治疗",
            "base_prescription": "参苓白术散加减：党参10g白术8g茯苓10g甘草3g山药8g",
            "base_prescription_usage": "水煎服每日1剂分2-3次温服连续5-7天可根据体重调整",
            "continue_prescription": "食欲好转加山楂神曲，大便成形减白术加苍术燥湿",
            "continue_prescription_usage": "症状改善后隔日1剂或制散剂混食物服用疗程10-14天",
            "suggest_prescription": "独参汤救急：人参15g单煎或安宫牛黄丸清热开窍",
            "suggest_prescription_usage": "紧急时与西医补液抗感染同时进行中药小量频服"
        }
    ]
    
    result = format_json_herb_diagnosis(sample_data)
    print("格式化结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 验证字段完整性
    expected_fields = [
        "zhengming", "description", "p", "therapy", "base", "continue", "suggest",
        "base_prescription", "base_prescription_usage", 
        "continue_prescription", "continue_prescription_usage",
        "suggest_prescription", "suggest_prescription_usage"
    ]
    
    if result:
        missing_fields = []
        for field in expected_fields:
            if field not in result[0]:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ 缺失字段: {missing_fields}")
        else:
            print("✅ 所有字段完整")
            print(f"✅ 概率值类型: {type(result[0]['p'])}, 值: {result[0]['p']}")

def test_herb_diagnosis_class():
    """测试HerbDiagnosis类"""
    print("\n=== 测试HerbDiagnosis类 ===")
    
    # 创建实例（不会真正初始化AgentScope，因为没有环境变量）
    herb_diagnosis = HerbDiagnosis()
    
    # 测试示例数据处理
    result = herb_diagnosis.test_with_sample_data()
    print("HerbDiagnosis类测试结果:")
    if result:
        print(f"✅ 成功处理 {len(result)} 条诊断记录")
        for i, item in enumerate(result):
            print(f"诊断 {i+1}: {item['zhengming']} (概率: {item['p']})")
    else:
        print("❌ 处理失败")

if __name__ == "__main__":
    test_probability_parsing()
    test_herb_diagnosis_formatting()
    test_herb_diagnosis_class()
    print("\n=== 测试完成 ===")
