import json
import re


def fix_broken_json(text: str) -> str:
    # 1. 修复 key 没有被正确关闭的情况："key:"value" -> "key": "value"
    text = re.sub(r'"([^"]+?):', r'"\1":', text)

    # 2. 确保所有 key 都正确带引号（避免末尾漏掉引号）
    text = re.sub(r'(?<=\{|,)\s*([a-zA-Z0-9_]+)\s*:', r'"\1":', text)

    # 3. 修复 key-value 之间缺失逗号的问题（通过换行/字符串拼接方式时常见）
    text = re.sub(r'"\s*([^"]+)"\s*:\s*"([^"]+)"\s*"(?![:,}\]])', r'"\1": "\2",', text)

    # 4. 尝试去除多余的尾随逗号（在最后一个元素后）
    text = re.sub(r',\s*([}\]])', r'\1', text)

    return text

def validate_and_fix(json_string: str):
    fixed = fix_broken_json(json_string)
    try:
        parsed = json.loads(fixed)
        return parsed
    except json.JSONDecodeError as e:
        print("修复失败：", e)
        return None

# # 示例
# broken_json = '''[{"zhengming":"肺热壅盛兼湿热下注","description":"精神不振与食欲不振为邪热内郁之象；浓鼻液与浓眼屎属肺经郁火；喷嚏乃风热犯肺；拉稀为湿热下迫大肠所致","p":0.85,"therapy":"清泻肺火佐以清热利湿","base":"保持环境通风干燥避免潮湿闷热饮食清淡少油腻多饮温水定时定量喂易消化食物如小米粥南瓜泥并保证充足休息减少剧烈运动","continue":"每日早晚观察体温呼吸频率粪便颜色质地及气味记录食欲饮水量变化若出现持续高热或血便立即复诊","suggest":"若出现高热不退抽搐或便血不止应立即送至具备中西结合诊疗条件的动物医院接受静脉补液抗生素及对症支持治疗以免延误病情危及生命健康","base_prescription":"银翘散合葛根芩连汤加减(金银花连翘葛根黄芩黄连甘草)","base_prescription_usage:"上方水煎取汁200毫升分早晚两次温服连用三日观察效果根据症状变化调整药味剂量",continue_prescription:"麻杏石甘汤加味(麻黄杏仁石膏甘草栀子车前子泽泻)去表邪清里热",continue_prescription_usage:"水煎取汁150毫升日服两次连服五至七日期间监测体重与排便状况必要时减量或停药",suggest_prescription:"清瘟败毒饮合白头翁汤大剂急煎配合西药头孢曲松钠静脉滴注及电解质平衡支持疗法",suggest_prescription_usage:"中药急煎浓缩至100毫升每四小时灌胃一次同时由执业兽医师实施静脉输液抗菌消炎纠正脱水酸中毒中西并用严密监护直至病情稳定"}]'''

# parsed_json = validate_and_fix(broken_json)
# if parsed_json:
#     print("✅ 修复并成功解析 JSON")
#     print(json.dumps(parsed_json, ensure_ascii=False, indent=2))