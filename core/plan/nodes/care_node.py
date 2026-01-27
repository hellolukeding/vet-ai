"""
护理计划生成节点

该节点负责根据宠物信息生成个性化的护理计划。
"""

import json
from datetime import datetime
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from backend.settings import settings
from config.logger import logger
from core.plan.state import CarePlan, State
from utils.json.extract_json_from_markdown import extract_json_from_markdown
from utils.llm.rate_limiter import get_global_rate_limiter
from utils.llm.retry_helper import retry_on_rate_limit, RetryConfig


class CarePlanSchema(BaseModel):
    """护理计划的结构化输出模式"""
    grooming: list[str] = Field(default_factory=list, description="美容护理建议")
    medical: list[str] = Field(default_factory=list, description="医疗护理建议")
    exercise: list[str] = Field(default_factory=list, description="运动建议")
    vaccination: list[str] = Field(default_factory=list, description="疫苗接种计划")
    environment: list[str] = Field(default_factory=list, description="环境管理建议")


async def CareNode(state: State) -> Dict:
    """
    护理计划生成节点

    基于宠物的基本信息、健康状况和生活环境，生成全面的护理计划，
    包括美容、医疗、运动、疫苗接种和环境管理建议。

    Args:
        state: 当前工作流状态，包含宠物信息

    Returns:
        Dict: 包含护理计划和推理笔记的字典
    """
    import time
    start_time = time.time()

    logger.info("【CareNode】开始生成护理计划")
    logger.debug(f"State状态: nutrition_ready={state.flags.nutrition_plan_ready}, "
                f"care_ready={state.flags.care_plan_ready}")

    # 获取配置
    model_name = settings.MODEL_NAME or "deepseek-ai/DeepSeek-V3"
    base_url = settings.BASE_URL or "https://api-inference.modelscope.cn/v1"
    api_key = settings.API_KEY or ""
    temperature = 0.2

    logger.debug(f"LLM配置: model={model_name}, temperature={temperature}")

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pet = state.pet

    logger.debug(
        f"宠物信息: name={pet.name}, species={pet.species}, breed={pet.breed}, "
        f"age={pet.age}, weight={pet.weight}, sex={pet.sex}")

    # 检查是否有足够的宠物信息
    if not pet.species:
        logger.warning("缺少宠物物种信息，无法生成护理计划")
        return {
            "care_plan": CarePlan(),
            "reasoning": {"care_agent_notes": "缺少宠物物种信息，无法生成护理计划"},
            "flags": {"care_plan_ready": "false"}
        }

    # 初始化LLM
    llm = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
    )

    # 获取全局速率限制器
    limiter = await get_global_rate_limiter(max_concurrent=1)

    # 配置重试参数
    retry_config = RetryConfig(max_retries=3, initial_delay=2.0)

    # 构建宠物信息描述
    weight_str = f"{pet.weight}kg" if pet.weight else "未提供"
    neutered_str = "是" if pet.neutered == "true" else (
        "否" if pet.neutered == "false" else "未提供")
    health_str = ", ".join(
        pet.health_conditions) if pet.health_conditions else "无特殊健康问题"

    pet_description = f"""
宠物信息：
- 名称：{pet.name or "未提供"}
- 物种：{pet.species}
- 品种：{pet.breed or "未提供"}
- 年龄：{pet.age or "未提供"}
- 体重：{weight_str}
- 性别：{pet.sex or "未提供"}
- 是否绝育：{neutered_str}
- 健康状况：{health_str}
- 活动水平：{pet.activity_level or "中等"}
"""

    # 构建提示
    system_instructions = f"""
当前时间：{current_time}
你是一位经验丰富的宠物护理专家，精通各类宠物的日常护理和健康管理。

任务：根据宠物信息生成全面的护理计划，返回严格的JSON格式。

JSON Schema:
{{
    "grooming": [str],        # 美容护理建议（3-6项），如刷牙、梳毛、洗澡、修剪指甲等
    "medical": [str],         # 医疗护理建议（3-6项），如定期体检、驱虫、牙齿检查等
    "exercise": [str],        # 运动建议（3-5项），如散步时长、运动类型、频率等
    "vaccination": [str],     # 疫苗接种计划（2-5项），根据年龄和物种
    "environment": [str]      # 环境管理建议（3-5项），如温度、安全措施、清洁等
}}

要求：
- 美容护理要具体到频率和方法，考虑品种特点（如长毛犬需更频繁梳理）
- 医疗护理要包含预防性保健和针对健康状况的特殊护理
- 运动建议要考虑年龄、体重、品种和健康状况（如老年犬减少剧烈运动）
- 疫苗计划要根据物种、年龄提供标准疫苗建议（如幼犬核心疫苗、成年犬年度加强）
- 环境管理要考虑物种习性和安全（如猫需要垂直空间、犬需要安全围栏等）
- 所有建议必须科学合理，符合兽医护理标准
- 每个类别至少提供2-3条具体建议
- 严格返回JSON，不要额外文本
- 不要使用Markdown代码块格式
"""

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instructions),
        HumanMessage(content=pet_description)
    ])

    # 调用LLM（使用速率限制和重试机制）
    reasoning_notes = ""

    # 使用速率限制器确保不会超过API并发限制
    async with limiter:
        try:
            logger.debug("调用LLM生成护理计划（智谱AI不支持结构化输出，使用普通调用）")

            # 定义普通调用函数
            async def call_llm():
                messages = prompt.format_messages()
                raw_response = await llm.ainvoke(messages)
                content = extract_json_from_markdown(raw_response.content)
                response_dict = json.loads(content)
                return CarePlanSchema(**response_dict)

            # 使用重试机制调用LLM
            response = await retry_on_rate_limit(
                call_llm,
                config=retry_config
            )

            reasoning_notes = "成功生成护理计划"
            logger.info("护理计划生成成功")

        except Exception as e:
            logger.error(f"护理计划生成失败: {e}")
            reasoning_notes = f"护理计划生成失败: {e}"
            return {
                "care_plan": CarePlan(),
                "reasoning": {"care_agent_notes": reasoning_notes},
                "flags": {"care_plan_ready": "false"}
            }

    # 转换为CarePlan对象
    plan_dict = response.model_dump() if hasattr(
        response, "model_dump") else response
    care_plan = CarePlan(**plan_dict)

    # 更新推理笔记
    reasoning_notes += f"\n- 美容护理建议数量：{len(care_plan.grooming)}"
    reasoning_notes += f"\n- 医疗护理建议数量：{len(care_plan.medical)}"
    reasoning_notes += f"\n- 运动建议数量：{len(care_plan.exercise)}"
    reasoning_notes += f"\n- 疫苗接种项目数量：{len(care_plan.vaccination)}"
    reasoning_notes += f"\n- 环境管理建议数量：{len(care_plan.environment)}"

    logger.info("护理计划生成完成")
    logger.debug(f"护理计划详情: {reasoning_notes}")

    elapsed_time = time.time() - start_time
    logger.info(f"【CareNode】完成，耗时: {elapsed_time:.2f}秒")

    return {
        "care_plan": care_plan,
        "reasoning": {"care_agent_notes": reasoning_notes},
        "flags": {"care_plan_ready": "true"}  # 重要：标记护理计划已完成
    }
