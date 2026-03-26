"""
中药方剂推荐节点 - 根据证型推荐中药方剂
"""

import json
from datetime import datetime
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config.logger import logger
from core.langgraph.state_herb import (
    HerbalPrescriptionItem,
    TCMZhengmingItem,
    TCAgentState,
)
from core.llm_factory import create_chat_llm
from utils.json.extract_json_from_markdown import extract_json_from_markdown


class HerbalPrescriptionSchema(BaseModel):
    """中药方剂schema"""

    prescriptions: List[HerbalPrescriptionItem] = Field(..., description="方剂列表")


async def HerbPharmacistNode(
    state: TCAgentState,
) -> Dict[str, List[HerbalPrescriptionItem]]:
    """根据中医证型推荐中药方剂

    Args:
        state: TCAgentState with zhengming

    Returns:
        dict with prescriptions key containing list of HerbalPrescriptionItem
    """
    temperature = 0.4

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    zhengming: List[TCMZhengmingItem] = getattr(state, "zhengming", []) or state.get(
        "zhengming", []
    )

    if not zhengming:
        logger.warning("中药方剂：没有证型诊断结果")
        return {"prescriptions": []}

    try:
        llm = create_chat_llm(temperature=temperature)
    except Exception as e:
        logger.error(f"中药方剂节点LLM初始化失败: {e}")
        logger.warning("中药方剂LLM配置不可用，不提供默认方剂以确保安全性")
        return {"prescriptions": []}

    # 构建证型信息
    zhengming_text = "中医证型诊断：\n"
    for idx, z in enumerate(zhengming[:5], 1):
        name = getattr(z, "zhengming", "") or (
            z.get("zhengming") if isinstance(z, dict) else ""
        )
        desc = getattr(z, "description", "") or (
            z.get("description") if isinstance(z, dict) else ""
        )
        prob = getattr(z, "probability", None) or (
            z.get("probability") if isinstance(z, dict) else 0
        )
        therapy = getattr(z, "therapy", "") or (
            z.get("therapy") if isinstance(z, dict) else ""
        )
        zhengming_text += (
            f"{idx}. {name} (概率: {prob})\n   治法: {therapy}\n   依据: {desc}\n"
        )

    # 中药方剂系统提示
    system_instructions = f"""
    当前时间：{current_time}
    你是一位中兽医方剂专家（中文输出），精通中药方剂学。

    ## 任务
    根据中医证型诊断，推荐合适的中药方剂。返回严格的JSON。

    ## ⚠️ 安全要求（CRITICAL）
    1. **仅推荐经典方剂**：使用经过长期验证的经典方剂（如参苓白术散、银翘散等）
    2. **剂量安全**：推荐常用剂量范围，明确单位（克g）
    3. **配伍禁忌**：注意十八反、十九畏等配伍禁忌
    4. **毒性药材**：谨慎使用有毒中药材（如附子、半夏等），需注明炮制方法
    5. **体质差异**：考虑宠物体重、年龄、体质差异

    ## 推理步骤
    1. **证型分析**：理解每个证型的病机
    2. **方证对应**：选择与证型对应的主方
    3. **随证加减**：根据具体症状加减药物
    4. **剂量确定**：根据宠物体重确定剂量
    5. **用法说明**：明确煎服方法和疗程

    ## 输出格式
    JSON: {{"prescriptions": [{{"zhengming": str, "prescription_type": str, "prescription_name": str, "composition": str, "usage": str}}]}}

    ## 方剂类型说明
    - **基础方**：用于该证型的基础治疗方剂
    - **加减方**：根据病情变化对方剂进行加减
    - **急救方**：用于急重症的救治方剂

    ## 方剂推荐示例
    证型：脾胃虚弱夹湿

    期望输出：
    {{
      "prescriptions": [
        {{"zhengming": "脾胃虚弱夹湿", "prescription_type": "基础方", "prescription_name": "参苓白术散加减", "composition": "党参10g、白术8g、茯苓10g、甘草3g、山药8g、扁豆8g、莲子6g、薏苡仁10g、砂仁3g（后下）", "usage": "水煎服，每日1剂，分2-3次温服，连续5-7天。可根据体重调整剂量（小型犬减半，大型犬增加1/3）。"}},
        {{"zhengming": "脾胃虚弱夹湿", "prescription_type": "加减方", "prescription_name": "食欲好转加减方", "composition": "原方加山楂6g、神曲6g以消食导滞", "usage": "症状改善后使用，隔日1剂或制散剂混食物服用，疗程10-14天。"}},
        {{"zhengming": "脾胃虚弱夹湿", "prescription_type": "急救方", "prescription_name": "独参汤", "composition": "人参15g（单煎）", "usage": "紧急时使用，小量频服，配合西医补液支持疗法。"}}
      ]
    }}

    ## 要求
    - `zhengming` 对应的中医证名
    - `prescription_type` 方剂类型（基础方/加减方/急救方）
    - `prescription_name` 方剂名称（优先使用经典方名）
    - `composition` 方剂组成，包括药物和剂量（单位：克g）
    - `usage` 用法用量，包括煎服方法、疗程、注意事项
    - 每个证型最多推荐3个方剂（1个基础方，1个加减方，1个急救方）
    - 整体不要超过15个方剂
    - 剂量需根据宠物体重调整，提供参考范围
    - 严格只输出 JSON，不要使用Markdown代码块包装结果
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_instructions),
            HumanMessage(content=zhengming_text),
        ]
    )

    # 尝试使用结构化输出
    try:
        logger.info("尝试使用结构化输出推荐中药方剂")
        structured_llm = llm.with_structured_output(
            HerbalPrescriptionSchema, method="json_schema"
        )
        messages = prompt.format_messages()
        response = await structured_llm.ainvoke(messages)
        logger.info("中药方剂结构化输出成功")
    except Exception as e:
        logger.warning(f"结构化输出调用失败: {e}，尝试使用普通 LLM + JSON 解析")
        try:
            messages = prompt.format_messages()
            raw_response = await llm.ainvoke(messages)
            logger.info(f"LLM 原始响应: {raw_response.content[:500]}...")

            content = extract_json_from_markdown(raw_response.content)
            logger.debug(f"提取的 JSON 内容: {content}")
            response = json.loads(content)
            logger.info("JSON 解析成功")
        except Exception as e2:
            logger.error(f"中药方剂推荐完全失败: {e2}")
            logger.warning("中药方剂推荐失败，返回空列表以确保安全性")
            return {"prescriptions": []}

    # 规范化输出
    try:
        if hasattr(response, "model_dump"):
            response = response.model_dump()
            logger.debug(
                f"转换为字典: {list(response.keys()) if isinstance(response, dict) else type(response)}"
            )

        prescription_list = (
            response.get("prescriptions") if isinstance(response, dict) else None
        )
        if not isinstance(prescription_list, list):
            logger.warning(f"prescriptions 字段不是列表: {type(prescription_list)}")
            prescription_list = []

        normalized: List[HerbalPrescriptionItem] = []
        for item in prescription_list:
            zhengming = item.get("zhengming", "")
            prescription_type = item.get("prescription_type", "")
            prescription_name = item.get("prescription_name", "")
            composition = item.get("composition", "")
            usage = item.get("usage", "")
            normalized.append(
                HerbalPrescriptionItem(
                    zhengming=zhengming,
                    prescription_type=prescription_type,
                    prescription_name=prescription_name,
                    composition=composition,
                    usage=usage,
                )
            )

        logger.info(f"成功规范化 {len(normalized)} 个中药方剂")
        return {"prescriptions": normalized}

    except Exception as e:
        logger.error(f"中药方剂解析失败: {e}", exc_info=True)
        logger.warning("方剂解析失败，返回空列表以确保安全性")
        return {"prescriptions": []}
