import os
import re
from typing import Any, Dict, List

import agentscope
from agentscope.agents import DialogAgent
from agentscope.message import Msg
from dotenv import load_dotenv

from config.logger import logger


def extract_table_only(text: str) -> str:
    """从文本中提取第一个 Markdown 表格块"""
    pattern = r"(\|.+\|(?:\n\|[-\s|]+\|)?(?:\n\|.*\|)+)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else text


def parse_diagnosis_table(table_str: str) -> List[Dict[str, str]]:
    """
    解析Markdown表格，自动补齐缺失列，避免因列数不匹配导致丢失整行
    """
    lines = [line.strip() for line in table_str.strip().split('\n') if line.strip()]
    if len(lines) < 3:
        return []

    headers = [h.strip() for h in lines[0].strip('|').split('|')]
    expected_col_count = len(headers)

    results = []

    for line in lines[2:]:  # 跳过分隔线
        cols = [c.strip() for c in line.strip('|').split('|')]
        if len(cols) < expected_col_count:
            # 补齐缺失列
            cols += [''] * (expected_col_count - len(cols))
            logger.warning(f"发现列数不足，自动补齐：{cols}")
        if len(cols) != expected_col_count:
            logger.warning(f"跳过异常行，列数不匹配：{line}")
            continue
        results.append(dict(zip(headers, cols)))

    return results


def parse_probability(p_value: str) -> float:
    """
    尝试从字符串中提取概率值，如果无法解析则返回默认值
    """
    if not p_value:
        return 0.0
    
    # 移除空格和常见的中文字符
    p_clean = p_value.strip()
    
    # 尝试直接转换为浮点数
    try:
        return float(p_clean)
    except ValueError:
        pass
    
    # 尝试提取数字（支持百分比）
    import re
    number_pattern = r'(\d+(?:\.\d+)?)'
    matches = re.findall(number_pattern, p_clean)
    
    if matches:
        try:
            num = float(matches[0])
            # 如果包含%符号，转换为小数
            if '%' in p_clean:
                return num / 100.0
            # 如果数字大于1，可能是百分比格式
            elif num > 1:
                return num / 100.0
            else:
                return num
        except ValueError:
            pass
    
    # 根据关键词给出默认概率值
    if any(keyword in p_clean for keyword in ['良好', '优', '高']):
        return 0.8
    elif any(keyword in p_clean for keyword in ['一般', '中等', '谨慎']):
        return 0.6
    elif any(keyword in p_clean for keyword in ['差', '低', '严重', '危险']):
        return 0.3
    
    logger.warning(f"无法解析概率值: {p_value}，使用默认值 0.5")
    return 0.5


def format_json_herb_diagnosis(parsed: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """格式化中医诊断结果"""
    result = []
    for row in parsed:
        try:
            p_value = row.get("p", "0.0")
            probability = parse_probability(p_value)
            
            result.append({
                "zhengming": row.get("zhengming", ""),
                "description": row.get("description", ""),
                "p": probability,
                "therapy": row.get("therapy", ""),
                "base": row.get("base", ""),
                "continue": row.get("continue", ""),
                "suggest": row.get("suggest", ""),
                "base_prescription": row.get("base_prescription", ""),
                "base_prescription_usage": row.get("base_prescription_usage", ""),
                "continue_prescription": row.get("continue_prescription", ""),
                "continue_prescription_usage": row.get("continue_prescription_usage", ""),
                "suggest_prescription": row.get("suggest_prescription", ""),
                "suggest_prescription_usage": row.get("suggest_prescription_usage", ""),
            })
            logger.info(f"成功格式化中医诊断: {row.get('zhengming', 'Unknown')} - 概率: {probability}")
        except Exception as e:
            logger.warning(f"格式化单行失败: {e}, 行数据: {row}")
            # 即使格式化失败，也尝试保留基本信息
            result.append({
                "zhengming": row.get("zhengming", ""),
                "description": row.get("description", ""),
                "p": 0.5,  # 默认概率
                "therapy": row.get("therapy", ""),
                "base": row.get("base", ""),
                "continue": row.get("continue", ""),
                "suggest": row.get("suggest", ""),
                "base_prescription": row.get("base_prescription", ""),
                "base_prescription_usage": row.get("base_prescription_usage", ""),
                "continue_prescription": row.get("continue_prescription", ""),
                "continue_prescription_usage": row.get("continue_prescription_usage", ""),
                "suggest_prescription": row.get("suggest_prescription", ""),
                "suggest_prescription_usage": row.get("suggest_prescription_usage", ""),
            })
    return result


def format_json_diagnosis(parsed: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """兼容原有西医诊断格式的函数"""
    result = []
    for row in parsed:
        try:
            p_value = row.get("p", "0.0")
            probability = parse_probability(p_value)
            
            result.append({
                "disease": row.get("disease", ""),
                "description": row.get("description", ""),
                "p": probability,
                "base": row.get("base", ""),
                "continue": row.get("continue", ""),
                "suggest": row.get("suggest", ""),
                "base_medicine": row.get("base_medicine", ""),
                "base_medicine_usage": row.get("base_medicine_usage", ""),
                "continue_medicine": row.get("continue_medicine", ""),
                "continue_medicine_usage": row.get("continue_medicine_usage", ""),
                "suggest_medicine": row.get("suggest_medicine", ""),
                "suggest_medicine_usage": row.get("suggest_medicine_usage", ""),
            })
            logger.info(f"成功格式化诊断: {row.get('disease', 'Unknown')} - 概率: {probability}")
        except Exception as e:
            logger.warning(f"格式化单行失败: {e}, 行数据: {row}")
            # 即使格式化失败，也尝试保留基本信息
            result.append({
                "disease": row.get("disease", ""),
                "description": row.get("description", ""),
                "p": 0.5,  # 默认概率
                "base": row.get("base", ""),
                "continue": row.get("continue", ""),
                "suggest": row.get("suggest", ""),
                "base_medicine": row.get("base_medicine", ""),
                "base_medicine_usage": row.get("base_medicine_usage", ""),
                "continue_medicine": row.get("continue_medicine", ""),
                "continue_medicine_usage": row.get("continue_medicine_usage", ""),
                "suggest_medicine": row.get("suggest_medicine", ""),
                "suggest_medicine_usage": row.get("suggest_medicine_usage", ""),
            })
    return result


class HerbDiagnosis:
    def __init__(self):
        load_dotenv(".env")
        self.model_name = os.getenv("model_name")
        self.base_url = os.getenv("base_url")
        self.api_key = os.getenv("api_key")
        self.sys_prompt = None
        self.initialized = False
        self.agent: DialogAgent = None

        logger.info(f"Model Name: {self.model_name}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"API Key: {self.api_key}")

        if self.model_name and self.base_url and self.api_key:
            try:
                agentscope.init(
                    model_configs=[
                        {
                            "model_type": "openai_chat",
                            "config_name": "diagnosis",
                            "model_name": self.model_name,
                            "api_key": self.api_key,
                            "client_args": {
                                "base_url": self.base_url,
                            },
                            "generate_args": {
                                "max_tokens": 2048,
                                "temperature": 0.8,
                                "top_p": 0.8,
                            },
                        },
                    ]
                )
                self.initialized = True
                self._init_prompt()
                self._init_agent()
            except Exception as e:
                logger.error(f"AgentScope 初始化失败: {e}")
        else:
            logger.warning("模型配置不完整，AgentScope 未初始化")

    def _init_prompt(self) -> None:
        self.sys_prompt = """你是中兽医专家，请根据以下症状严格输出包含13列的Markdown表格中医诊断结果，不得缺失列，尤其是最后一列不能截断：

| zhengming | description | p | therapy | base | continue | suggest | base_prescription | base_prescription_usage | continue_prescription | continue_prescription_usage | suggest_prescription | suggest_prescription_usage |
|-----------|-------------|---|---------|------|----------|---------|-------------------|-------------------------|----------------------|----------------------------|---------------------|---------------------------|

字段说明：
- zhengming: 中医证名
- description: 病理分析描述
- p: 诊断概率(0-1之间的数字)
- therapy: 治法
- base: 基础护理
- continue: 继续观察
- suggest: 建议就医情况
- base_prescription: 基础方剂
- base_prescription_usage: 基础方剂用法
- continue_prescription: 加减方剂
- continue_prescription_usage: 加减方剂用法
- suggest_prescription: 急救方剂
- suggest_prescription_usage: 急救方剂用法

所有字段必须完整输出，p字段必须是0-1之间的数字，不得多余文字。请开始中医诊断："""

    def _init_agent(self) -> None:
        self.agent = DialogAgent(
            name="diagnosis",
            model_config_name="diagnosis",
            sys_prompt=self.sys_prompt,
        )

    def diagnosis(self, desc: str) -> List[Dict[str, Any]]:
        if not self.initialized or self.agent is None:
            logger.error("中医诊断模型未初始化")
            return []

        user_message = f"""症状描述：{desc}

请基于中医理论进行分析，严格输出符合要求的中医诊断表格格式，字段齐全，不得缺失。特别注意p字段必须是0-1之间的数字。"""

        task = Msg("User", user_message, "user")
        result = self.agent(task)
        logger.info(f"Raw Result: {result.content}")

        cleaned_content = result.content
        logger.info(f"Cleaned Result: {cleaned_content}")

        try:
            parsed = parse_diagnosis_table(cleaned_content)
            logger.info(f"Parsed Result: {parsed}")
            return format_json_herb_diagnosis(parsed)
        except Exception as e:
            logger.error(f"中医诊断解析失败: {e}")
            return []

    def test_with_sample_data(self) -> List[Dict[str, Any]]:
        """使用示例数据测试格式化功能"""
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
            },
            {
                "zhengming": "外感风热犯肺",
                "description": "根据鼻涕眼屎打喷嚏精神不振等症状判断外邪犯表肺气失宣热邪上扰清窍卫表不固",
                "p": "0.68",
                "therapy": "疏风清热，宣肺解表，清利头目，调和营卫",
                "base": "空气流通避免风吹，饮食清淡多汁，补充维生素，清洁分泌物",
                "continue": "观察体温变化呼吸频率，监测分泌物性质，防继发感染",
                "suggest": "高热呼吸困难咳嗽加重或脓性分泌物需及时就医防肺炎",
                "base_prescription": "银翘散加减：银花12g连翘10g薄荷5g牛蒡子8g桔梗6g甘草3g",
                "base_prescription_usage": "轻煎10分钟每日1剂温服分3次薄荷后下连服3-5天",
                "continue_prescription": "热重加黄芩栀子，咳嗽加杏仁桔梗，鼻塞加苍耳子辛夷",
                "continue_prescription_usage": "根据症状调整药量症状缓解后减量续服2-3天巩固",
                "suggest_prescription": "清瘟败毒散：生石膏30g知母10g黄连5g黄芩10g",
                "suggest_prescription_usage": "高热时配合物理降温西医退烧药中药频服小量每2-3小时1次"
            }
        ]
        
        logger.info("测试中医诊断格式化功能")
        return format_json_herb_diagnosis(sample_data)