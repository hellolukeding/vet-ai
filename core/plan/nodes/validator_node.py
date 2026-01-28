"""
验证节点

该节点负责验证营养计划和护理计划的一致性和安全性。
"""

from datetime import datetime
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from backend.settings import settings
from config.logger import logger
from core.plan.state import State


async def ValidatorNode(state: State) -> Dict:
    """
    验证节点

    检查营养计划和护理计划之间的一致性，识别潜在的冲突或风险，
    并进行安全性评估。

    Args:
        state: 当前工作流状态，包含营养计划和护理计划

    Returns:
        Dict: 包含风险分析和冲突检测结果的字典
    """
    logger.info("【ValidatorNode】开始验证计划一致性")

    # 获取配置
    model_name = settings.MODEL_NAME or "deepseek-ai/DeepSeek-V3"
    base_url = settings.BASE_URL or "https://api-inference.modelscope.cn/v1"
    api_key = settings.API_KEY or ""
    temperature = 0.2

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pet = state.pet
    nutrition_plan = state.nutrition_plan
    care_plan = state.care_plan

    # 检查计划是否都已生成
    nutrition_ready = state.flags.nutrition_plan_ready == "true"
    care_ready = state.flags.care_plan_ready == "true"
    if not nutrition_ready or not care_ready:
        logger.warning(
            f"计划未完成，跳过验证 - 营养计划: {nutrition_ready}, 护理计划: {care_ready}")
        return {
            "reasoning": {
                "risk_analysis": "营养或护理计划未完成，无法进行完整的风险评估。建议咨询专业兽医进行个性化评估。",
                "contradictions": []
            }
        }

    # 初始化LLM
    llm = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
    )

    # 构建验证上下文
    health_str = ", ".join(
        pet.health_conditions) if pet.health_conditions else "无特殊健康问题"
    allergies_str = ", ".join(pet.allergies) if pet.allergies else "无已知过敏"

    validation_context = f"""
宠物信息：
- 物种：{pet.species}
- 品种：{pet.breed or "未提供"}
- 年龄：{pet.age or "未提供"}
- 健康状况：{health_str}
- 过敏源：{allergies_str}

营养计划：
- 每日卡路里：{nutrition_plan.daily_calories}kcal
- 推荐食物：{", ".join(nutrition_plan.recommended_foods[:5])}{"..." if len(nutrition_plan.recommended_foods) > 5 else ""}
- 避免食物：{", ".join(nutrition_plan.avoid_foods)}
- 补充剂：{", ".join(nutrition_plan.supplements)}

护理计划：
- 运动建议：{", ".join(care_plan.exercise[:3])}{"..." if len(care_plan.exercise) > 3 else ""}
- 医疗护理：{", ".join(care_plan.medical[:3])}{"..." if len(care_plan.medical) > 3 else ""}
"""

    # 构建提示
    system_instructions = f"""
当前时间：{current_time}
你是一位资深的宠物健康顾问，负责审核营养和护理计划的一致性和安全性。

任务：分析以下营养计划和护理计划，识别潜在问题。

请检查以下方面：
1. 营养计划是否与健康状况相符（如糖尿病宠物的卡路里和碳水控制）
2. 推荐食物是否与过敏源冲突
3. 运动强度是否与营养摄入匹配（高运动量需要更多能量）
4. 运动建议是否考虑了健康状况（如关节炎应避免剧烈运动）
5. 补充剂是否与医疗护理建议一致
6. 是否存在其他潜在风险

以简洁的中文段落形式回复：
1. 首先给出整体风险评估（低风险/中等风险/高风险）和总结
2. 如果发现具体问题，列出每个问题（每行一个问题，使用 "- " 开头）
3. 如果没有发现问题，说明"未发现明显冲突或风险"

不要返回JSON，只需要自然语言文本。
"""

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instructions),
        HumanMessage(content=validation_context)
    ])

    # 调用LLM
    risk_analysis = ""
    contradictions: List[str] = []

    try:
        logger.debug("调用LLM进行风险评估")
        messages = prompt.format_messages()
        response = await llm.ainvoke(messages)
        risk_analysis = response.content.strip()
        logger.info("风险评估完成")

        # 提取具体的冲突项（以 "- " 开头的行）
        lines = risk_analysis.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("- ") or line.startswith("• "):
                contradiction = line[2:].strip()
                if contradiction and "未发现" not in contradiction and "无明显" not in contradiction:
                    contradictions.append(contradiction)

        if contradictions:
            logger.warning(f"发现 {len(contradictions)} 个潜在问题")
        else:
            logger.info("未发现明显冲突")

    except Exception as e:
        logger.error(f"验证调用失败: {e}")
        risk_analysis = f"验证过程出错，建议咨询专业兽医进行人工审核：{e}"

    return {
        "reasoning": {
            "risk_analysis": risk_analysis,
            "contradictions": contradictions
        }
    }
