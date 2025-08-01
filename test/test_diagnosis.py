import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.parser.table import parse_diagnosis_table, format_diagnosis_as_json
from core.ai_diagnosis.diagnosis import Diagnosis


def main():
    # 创建诊断实例
    diagnosis = Diagnosis()
    
    # 检查初始化状态
    if not diagnosis.initialized:
        print("❌ 诊断系统初始化失败，请检查环境变量配置")
        return
    
    print("✅ 诊断系统初始化成功")
    print(f"📊 使用模型: {diagnosis.model_name}")
    print(f"🔗 API地址: {diagnosis.base_url}")
    print()
    
    # 初始化agent
    print("🤖 正在初始化AI诊断agent...")
    diagnosis._init_agent()
    print("✅ Agent初始化完成")
    print()
    
    # 测试症状描述
    symptom_description = "姓名凯凯，为一雌性金毛犬，现年7岁，体重26 kg。送来时主诉:最近几天精神不好，食欲不振，有浓鼻液、浓眼屎，打喷嚏，拉稀。"
    
    print("🔍 开始诊断分析...")
    print(f"📋 症状描述: {symptom_description}")
    print()
    
    try:
        # 执行诊断
        res = diagnosis.diagnosis(symptom_description)
        
        print("📊 原始诊断结果:")
        print("=" * 80)
        print(f"类型: {type(res)}")
        print(f"内容: {res.content if hasattr(res, 'content') else str(res)}")
        print("=" * 80)
        print()
        
        # 解析表格数据
        try:
            # 传递文本内容而不是Msg对象
            table_content = res.content if hasattr(res, 'content') else str(res)
            dict_res = parse_diagnosis_table(table_content)
            
            print("📋 标准JSON格式诊断结果:")
            print("=" * 80)
            # 使用新的格式化函数输出JSON
            json_output = format_diagnosis_as_json(dict_res, indent=2)
            print(json_output)
            print("=" * 80)
            
        except Exception as parse_error:
            print(f"⚠️ 表格解析失败: {parse_error}")
            print("原始内容将直接显示")
        
    except Exception as e:
        print(f"❌ 诊断过程中出现错误: {e}")
        print(f"错误类型: {type(e).__name__}")
    
    
if __name__ == "__main__":
    main()
