"""
营养计划生成节点

该节点负责根据宠物信息生成个性化的营养计划。
"""

import json
from datetime import datetime
from typing import Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from backend.settings import settings
from config.logger import logger
from core.plan.state import NutritionPlan, State
from utils.json.extract_json_from_markdown import extract_json_from_markdown
from utils.llm.rate_limiter import get_global_rate_limiter
from utils.llm.retry_helper import RetryConfig, retry_on_rate_limit


class NutritionPlanSchema(BaseModel):
    """营养计划的结构化输出模式"""

    daily_calories: Optional[str] = Field(
        default=None, description="每日卡路里需求，返回字符串格式"
    )
    macro_ratio: dict[str, str] = Field(
        default_factory=dict, description="宏量营养素比例，值为字符串格式"
    )
    recommended_foods: list[str] = Field(default_factory=list, description="推荐食物")
    avoid_foods: list[str] = Field(default_factory=list, description="避免食物")
    supplements: list[str] = Field(default_factory=list, description="营养补充剂")
    feeding_schedule: list[str] = Field(default_factory=list, description="喂养时间表")


async def NutritionNode(state: State) -> Dict:
    """
    营养计划生成节点

    基于宠物的基本信息、健康状况和活动水平，生成个性化的营养计划，
    包括每日卡路里需求、营养比例、推荐食物、禁忌食物等。

    Args:
        state: 当前工作流状态，包含宠物信息

    Returns:
        Dict: 包含营养计划和推理笔记的字典
    """
    import time

    start_time = time.time()

    logger.info("【NutritionNode】开始生成营养计划")
    logger.debug(
        f"State状态: nutrition_ready={state.flags.nutrition_plan_ready}, "
        f"care_ready={state.flags.care_plan_ready}"
    )

    # 获取配置
    model_name = settings.MODEL_NAME or "deepseek-v4-flash"
    base_url = settings.BASE_URL or "https://api.deepseek.com"
    api_key = settings.API_KEY or ""
    temperature = 0.2

    logger.debug(
        f"LLM配置: model={model_name}, base_url={base_url}, temperature={temperature}"
    )

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pet = state.pet

    logger.debug(
        f"宠物信息: name={pet.name}, species={pet.species}, breed={pet.breed}, "
        f"age={pet.age}, weight={pet.weight}, sex={pet.sex}, neutered={pet.neutered}"
    )

    # 检查是否有足够的宠物信息
    if not pet.species:
        logger.warning("缺少宠物物种信息，无法生成营养计划")
        return {
            "nutrition_plan": NutritionPlan(),
            "reasoning": {
                "nutrition_agent_notes": "缺少宠物物种信息，无法生成营养计划"
            },
            "flags": {"nutrition_plan_ready": "false"},
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
    neutered_str = (
        "是"
        if pet.neutered == "true"
        else ("否" if pet.neutered == "false" else "未提供")
    )
    health_str = (
        ", ".join(pet.health_conditions) if pet.health_conditions else "无特殊健康问题"
    )
    allergies_str = ", ".join(pet.allergies) if pet.allergies else "无已知过敏"

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
- 过敏源：{allergies_str}
- 喂养历史：{pet.feeding_history or "未提供"}
- 活动水平：{pet.activity_level or "中等"}
"""

    # 构建提示
    system_instructions = f"""
当前时间：{current_time}
你是一位资深的宠物营养师，精通各类宠物的营养需求和饮食管理。

任务：根据宠物信息生成个性化营养计划，返回严格的JSON格式。

JSON Schema:
{{
    "daily_calories": str,             # 每日卡路里需求，返回字符串格式
    "macro_ratio": {{                  # 宏量营养素百分比
        "protein": str,                # 蛋白质百分比，字符串格式
        "fat": str,                    # 脂肪百分比，字符串格式
        "carbs": str                   # 碳水化合物百分比，字符串格式
    }},
    "recommended_foods": [str],        # 推荐食物列表（3-8项）
    "avoid_foods": [str],              # 应避免的食物列表（基于过敏和健康状况）
    "supplements": [str],              # 营养补充剂建议（0-5项）
    "feeding_schedule": [str]          # 喂养时间表（如 "早上7点 - 200g", "晚上6点 - 200g"）
}}

要求：
- 根据物种、年龄、体重、活动水平计算合理的每日卡路里需求
- 宏量营养素比例总和应为100，根据物种和健康状况调整
- 推荐食物要具体，包括商业宠物粮和天然食材
- 必须考虑健康状况和过敏源，列出应避免的食物
- 补充剂建议要有针对性（如老年犬推荐关节保健品）
- 喂养时间表要包含时间和分量建议
- 所有建议必须科学合理，符合兽医营养学标准
- 严格返回JSON，不要额外文本
- 不要使用Markdown代码块格式
"""

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_instructions),
            HumanMessage(content=pet_description),
        ]
    )

    # 调用LLM（使用速率限制和重试机制）
    reasoning_notes = ""

    # 使用速率限制器确保不会超过API并发限制
    async with limiter:
        try:
            logger.debug("调用LLM生成营养计划（智谱AI不支持结构化输出，使用普通调用）")

            # 定义普通调用函数
            async def call_llm():
                messages = prompt.format_messages()
                raw_response = await llm.ainvoke(messages)
                content = extract_json_from_markdown(raw_response.content)
                response_dict = json.loads(content)
                return NutritionPlanSchema(**response_dict)

            # 使用重试机制调用LLM
            response = await retry_on_rate_limit(call_llm, config=retry_config)

            reasoning_notes = "成功生成营养计划"
            logger.info("营养计划生成成功")

        except Exception as e:
            logger.error(f"营养计划生成失败: {e}")
            reasoning_notes = f"营养计划生成失败: {e}"
            return {
                "nutrition_plan": NutritionPlan(),
                "reasoning": {"nutrition_agent_notes": reasoning_notes},
                "flags": {"nutrition_plan_ready": "false"},
            }

    # 转换为NutritionPlan对象
    plan_dict = response.model_dump() if hasattr(response, "model_dump") else response

    # 【关键】提供默认值，避免空数组
    # recommended_foods: 空数组或null时提供默认值
    rf = plan_dict.get("recommended_foods")
    if not rf or len(rf) == 0:
        plan_dict["recommended_foods"] = [
            "优质成犬粮",
            "煮熟的鸡胸肉",
            "糙米",
            "胡萝卜",
            "三文鱼",
        ]
        logger.debug("设置默认推荐食物")

    # avoid_foods: 空数组或null时提供默认值
    af = plan_dict.get("avoid_foods")
    if not af or len(af) == 0:
        plan_dict["avoid_foods"] = [
            "巧克力",
            "洋葱",
            "大蒜",
            "葡萄",
            "木糖醇",
            "煮熟的骨头",
        ]
        logger.debug("设置默认避免食物")

    # supplements: 空数组或null时提供默认值
    sup = plan_dict.get("supplements")
    if not sup or len(sup) == 0:
        plan_dict["supplements"] = ["深海鱼油（Omega-3）", "根据兽医建议添加其他补充剂"]
        logger.debug("设置默认补充剂")

    # feeding_schedule: 空数组或null时提供默认值
    fs = plan_dict.get("feeding_schedule")
    if not fs or len(fs) == 0:
        plan_dict["feeding_schedule"] = [
            "早上7点 - 早餐（约每日热量的50%）",
            "晚上6点 - 晚餐（约每日热量的50%）",
        ]
        logger.debug("设置默认喂养时间表")

    # macro_ratio: 空字典或null时提供默认值
    mr = plan_dict.get("macro_ratio")
    if not mr or len(mr) == 0:
        plan_dict["macro_ratio"] = {"protein": "25%", "fat": "15%", "carbs": "60%"}
        logger.debug("设置默认营养比例")

    # daily_calories: null或空时提供默认值
    dc = plan_dict.get("daily_calories")
    if not dc:
        plan_dict["daily_calories"] = (
            "根据宠物体重和活动水平计算（通常成年犬每公斤体重约需要30-50kcal）"
        )
        logger.debug("设置默认卡路里")

    nutrition_plan = NutritionPlan(**plan_dict)

    # 更新推理笔记
    reasoning_notes += f"\n- 每日卡路里：{nutrition_plan.daily_calories}kcal"
    reasoning_notes += (
        f"\n- 营养比例：蛋白质{nutrition_plan.macro_ratio.get('protein', 0)}%, "
    )
    reasoning_notes += f"脂肪{nutrition_plan.macro_ratio.get('fat', 0)}%, "
    reasoning_notes += f"碳水{nutrition_plan.macro_ratio.get('carbs', 0)}%"
    reasoning_notes += f"\n- 推荐食物数量：{len(nutrition_plan.recommended_foods)}"
    reasoning_notes += f"\n- 避免食物数量：{len(nutrition_plan.avoid_foods)}"

    logger.info("营养计划生成完成")
    logger.debug(f"营养计划详情: {reasoning_notes}")

    elapsed_time = time.time() - start_time
    logger.info(f"【NutritionNode】完成，耗时: {elapsed_time:.2f}秒")

    return {
        "nutrition_plan": nutrition_plan,
        "reasoning": {"nutrition_agent_notes": reasoning_notes},
        "flags": {"nutrition_plan_ready": "true"},  # 重要：标记营养计划已完成
    }
