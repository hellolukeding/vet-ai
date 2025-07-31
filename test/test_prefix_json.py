import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.parser.markdown_json_list_parser import extract_clean_json

def test_prefix_json():
    # 测试包含前缀的JSON字符串（模拟实际模型输出）
    test_output = '''DiagnosisAgent: [
{"disease":"细菌性呼吸道感染","p":0.4,"base":"隔离其他宠物避免传染，用湿棉球清理眼鼻分泌物，提供温热饮用水","continue":"口服抗生素需遵医嘱完成疗程，加强营养补充蛋白质和维生素C","suggest":"呼吸急促超过40次/分钟或拒食超过24小时需紧急就诊"},
{"disease":"犬瘟热","p":0.35,"base":"保持环境温暖干燥，提供充足饮水，喂食易消化食物如鸡肉粥","continue":"每日监测体温变化使用生理盐水清洁鼻腔和眼部分泌物","suggest":"出现抽搐持续高热或血便时立即送医"},
{"disease":"肠胃炎合并上呼吸道感染","p":0.25,"base":"禁食12小时后喂低脂易消化食物如白粥鸡胸肉"，"continue"："补充益生菌调理肠道口服补液盐防脱水"，"suggest"："腹泻带血或呕吐不止出现脱水症状时需立即就医"}
]'''
    
    result = extract_clean_json(test_output)
    print(f"解析结果: {result}")
    if result is not None:
        print(f"成功解析 {len(result)} 个诊断项")
        for i, item in enumerate(result):
            print(f"诊断项 {i+1}: {item['disease']} (概率: {item['p']})")
    else:
        print("解析失败")

if __name__ == "__main__":
    test_prefix_json()