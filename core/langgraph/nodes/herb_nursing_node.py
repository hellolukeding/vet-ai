"""
中医护理建议节点 - 根据证型生成中医护理建议
"""
import json
from datetime import datetime
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from backend.settings import settings
from config.logger import logger
from core.langgraph.state_herb import TCMNursingItem, TCMZhengmingItem, TCAgentState
from utils.json.extract_json_from_markdown import extract_json_from_markdown


class NursingSchema(BaseModel):
    """中医护理建议schema"""
    nursing: List[TCMNursingItem] = Field(..., description="护理建议列表")


async def HerbNursingNode(state: TCAgentState) -> Dict[str, List[TCMNursingItem]]:
    """根据中医证型生成护理建议

    Args:
        state: TCAgentState with zhengming

    Returns:
        dict with nursing key containing list of TCMNursingItem
    """
    # 获取配置
    model_name = settings.MODEL_NAME or "deepseek-ai/DeepSeek-V3"
    base_url = settings.BASE_URL or "https://api-inference.modelscope.cn/v1"
    api_key = settings.API_KEY or ""
    temperature = 0.5

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    zhengming: List[TCMZhengmingItem] = getattr(state, "zhengming", []) or state.get("zhengming", [])

    if not zhengming:
        logger.warning("中医护理：没有证型诊断结果")
        return {"nursing": []}

    llm = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
    )

    # 构建证型信息
    zhengming_text = "中医证型诊断：\n"
    for idx, z in enumerate(zhengming[:5], 1):
        name = getattr(z, "zhengming", "") or (z.get("zhengming") if isinstance(z, dict) else "")
        desc = getattr(z, "description", "") or (z.get("description") if isinstance(z, dict) else "")
        therapy = getattr(z, "therapy", "") or (z.get("therapy") if isinstance(z, dict) else "")
        zhengming_text += f"{idx}. {name}\n   治法: {therapy}\n   依据: {desc}\n"

    # 中医护理系统提示
    system_instructions = f"""
    当前时间：{current_time}
    你是一位中兽医护理专家，精通中医护理理论和宠物护理。

    ## 任务
    根据中医证型诊断，提供中医护理建议。返回严格的JSON。

    ## 护理原则
    1. **基础护理 (base)**：日常护理、饮食调理、环境管理
    2. **继续观察 (continue)**：需要观察的症状变化、监测指标
    3. **建议就医 (suggest)**：需要立即就医的警示信号

    ## 输出格式
    JSON: {{"nursing": [{{"category": str, "content": str}}]}}

    ## 护理建议示例
    证型：脾胃虚弱夹湿

    期望输出：
    {{
      "nursing": [
        {{"category": "base", "content": "饮食调理：给予易消化食物，如稀粥、肉泥，少量多餐。避免生冷、油腻、难消化食物。环境管理：保持温暖干燥，避免潮湿和直吹空调。适当运动：轻度活动促进气血运行，但避免过度劳累。"}},
        {{"category": "continue", "content": "观察食欲变化：每日记录进食量和精神状态。观察大便性状：注意大便次数、性状是否改善。监测体温：每日测量体温，观察是否恢复正常。"}},
        {{"category": "suggest", "content": "立即就医：持续呕吐超过24小时或呕吐物带血。高热不退（体温>39.5°C）或持续低体温。精神极度萎靡、昏迷或抽搐。完全拒食超过48小时，脱水明显。"}}
      ]
    }}

    ## 要求
    - `category` 只能是：base、continue、suggest 三个值之一
    - `content` 详细说明具体的护理措施
    - 每个类别最多提供 1-2 条建议
    - 结合中医理论（如脾胃虚弱宜温补，寒湿困脾宜保暖等）
    - 内容要具体可操作，不要泛泛而谈
    - 严格只输出 JSON，不要使用Markdown代码块包装结果
    """

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instructions),
        HumanMessage(content=zhengming_text)
    ])

    # 尝试使用结构化输出
    try:
        logger.info("尝试使用结构化输出生成中医护理建议")
        structured_llm = llm.with_structured_output(NursingSchema, method="json_schema")
        messages = prompt.format_messages()
        response = await structured_llm.ainvoke(messages)
        logger.info("中医护理结构化输出成功")
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
            logger.error(f"中医护理建议生成失败: {e2}")
            # 返回默认护理建议
            logger.warning("使用默认中医护理建议")
            return {"nursing": [
                TCMNursingItem(category="base", content="饮食清淡易消化，保持环境温暖干燥，适当运动"),
                TCMNursingItem(category="continue", content="观察症状变化，监测精神状态和体温"),
                TCMNursingItem(category="suggest", content="持续呕吐腹泻或高热应立即就医")
            ]}

    # 规范化输出
    try:
        if hasattr(response, "model_dump"):
            response = response.model_dump()
            logger.debug(f"转换为字典: {list(response.keys()) if isinstance(response, dict) else type(response)}")

        nursing_list = response.get("nursing") if isinstance(response, dict) else None
        if not isinstance(nursing_list, list):
            logger.warning(f"nursing 字段不是列表: {type(nursing_list)}")
            nursing_list = []

        normalized: List[TCMNursingItem] = []
        for item in nursing_list:
            category = item.get("category", "")
            content = item.get("content", "")
            normalized.append(TCMNursingItem(
                category=category,
                content=content
            ))

        logger.info(f"成功规范化 {len(normalized)} 条护理建议")
        return {"nursing": normalized}

    except Exception as e:
        logger.error(f"中医护理建议解析失败: {e}", exc_info=True)
        logger.warning("使用默认中医护理建议")
        return {"nursing": [
            TCMNursingItem(category="base", content="饮食清淡易消化，保持环境温暖干燥，适当运动"),
            TCMNursingItem(category="continue", content="观察症状变化，监测精神状态和体温"),
            TCMNursingItem(category="suggest", content="持续呕吐腹泻或高热应立即就医")
        ]}
