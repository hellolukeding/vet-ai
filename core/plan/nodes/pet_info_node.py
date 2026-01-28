"""
宠物信息提取节点

该节点负责从用户查询中提取和补全宠物基本信息。
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
from core.plan.state import PetInfo, State
from utils.json.extract_json_from_markdown import extract_json_from_markdown


class PetInfoSchema(BaseModel):
    """宠物信息提取的结构化输出模式"""
    name: Optional[str] = Field(default=None, description="宠物名称")
    species: Optional[str] = Field(default=None, description="物种类型")
    breed: Optional[str] = Field(default=None, description="品种")
    age: Optional[str] = Field(default=None, description="年龄")
    weight: Optional[str] = Field(default=None, description="体重（kg），返回字符串格式")
    sex: Optional[str] = Field(default=None, description="性别")
    neutered: Optional[str] = Field(default=None, description="是否绝育，返回'true'或'false'字符串")
    health_conditions: list[str] = Field(
        default_factory=list, description="健康状况")
    allergies: list[str] = Field(default_factory=list, description="过敏源")
    feeding_history: Optional[str] = Field(default=None, description="喂养历史")
    activity_level: Optional[str] = Field(default=None, description="活动水平")


async def PetInfoNode(state: State) -> Dict:
    """
    宠物信息提取节点

    从用户查询中提取宠物的基本信息，包括名称、物种、品种、年龄、体重等。
    如果信息不完整，会标记需要补全。

    Args:
        state: 当前工作流状态

    Returns:
        Dict: 包含更新后的宠物信息和标志的字典
    """
    import time
    start_time = time.time()

    logger.info("【PetInfoNode】开始提取宠物信息")
    logger.debug(f"用户查询: {state.user_query[:100] if state.user_query else '空'}...")

    # 获取配置
    model_name = settings.MODEL_NAME or "deepseek-ai/DeepSeek-V3"
    base_url = settings.BASE_URL or "https://api-inference.modelscope.cn/v1"
    api_key = settings.API_KEY or ""
    temperature = 0.3

    logger.debug(f"LLM配置: model={model_name}, base_url={base_url}, temperature={temperature}")

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_query = state.user_query or ""

    # 检查是否有初始宠物信息
    initial_pet_info = {}
    if state.pet:
        if state.pet.name:
            initial_pet_info["name"] = state.pet.name
        if state.pet.species:
            initial_pet_info["species"] = state.pet.species
        if state.pet.breed:
            initial_pet_info["breed"] = state.pet.breed
        if state.pet.age:
            initial_pet_info["age"] = state.pet.age
        if state.pet.weight:
            initial_pet_info["weight"] = state.pet.weight
        if state.pet.sex:
            initial_pet_info["sex"] = state.pet.sex
        if state.pet.neutered:
            initial_pet_info["neutered"] = state.pet.neutered

    if initial_pet_info:
        logger.debug(f"检测到初始宠物信息: {initial_pet_info}")

    if not user_query:
        logger.warning("用户查询为空，无法提取宠物信息")
        return {"flags": {"need_pet_info_completion": "true"}}

    # 初始化LLM
    llm = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
    )

    # 构建提示
    # 如果有初始宠物信息，添加到提示中
    initial_info_str = ""
    if initial_pet_info:
        initial_info_str = f"\n\n已知的宠物信息（请保留这些字段，不要覆盖为null）：\n{json.dumps(initial_pet_info, ensure_ascii=False, indent=2)}"

    system_instructions = f"""
当前时间：{current_time}
你是一位专业的宠物信息提取助手，需要从用户的查询中提取宠物的基本信息。

任务：从下面的用户查询中提取宠物信息，返回严格的JSON格式。{initial_info_str}

JSON Schema:
{{
    "name": str or null,
    "species": str or null,  # 如 "狗", "猫", "兔子"
    "breed": str or null,    # 如 "金毛", "波斯猫"
    "age": str or null,      # 如 "3岁", "6个月"
    "weight": str or null,   # 单位kg，返回字符串格式如 "30.5"
    "sex": str or null,      # "公" 或 "母"，或 "male" 或 "female"
    "neutered": str or null, # 返回字符串 "true" 或 "false"
    "health_conditions": list[str],  # 【重要】提取所有健康问题，如"食欲不振"、"呕吐"、"腹泻"、"精神萎靡"等，如果没有健康问题则返回[]
    "allergies": list[str],          # 提取所有过敏源，如"鸡肉"、"小麦"等，如果没有过敏则返回[]
    "feeding_history": str or null,
    "activity_level": str or null    # 根据描述判断："低"（很少运动）、"中"（正常散步）、"高"（活跃好动）
}}

重要提示：
- 【特别关注】仔细阅读用户描述，提取所有提到的健康问题和症状
- 例如："食欲不太好"应提取为health_conditions: ["食欲不振"或"食欲下降"]
- 例如："最近呕吐"应提取为health_conditions: ["呕吐"]
- 如果用户没有明确提到健康问题，health_conditions必须返回空数组[]而不是null
- 如果用户没有明确提到过敏，allergies必须返回空数组[]而不是null
- activity_level根据用户描述判断，如果未提及可根据品种特点推测（如金毛通常是"中"或"高"）
- 【重要】如果"已知的宠物信息"中已经提供了某个字段的值，必须保留该值，不要覆盖
- 只提取和补充明确提到的信息，未提到的字段保持已提供的值或设为 null
- species 和 breed 尅量用中文
- 不要编造未提及的信息
- 严格返回JSON，不要额外文本
- 不要使用Markdown代码块格式（```json ... ```）
"""

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instructions),
        HumanMessage(content=f"用户查询：{user_query}")
    ])

    # 调用LLM
    # 注意：智谱AI API 不支持结构化输出，直接使用普通调用
    try:
        logger.debug("调用LLM提取宠物信息（使用普通调用，智谱AI不支持结构化输出）")
        messages = prompt.format_messages()
        raw_response = await llm.ainvoke(messages)
        content = extract_json_from_markdown(raw_response.content)
        response_dict = json.loads(content)
        response = PetInfoSchema(**response_dict)
        logger.info("宠物信息提取成功")
    except Exception as e:
        logger.error(f"宠物信息提取失败: {e}")
        return {"flags": {"need_pet_info_completion": "true"}}

    # 转换为PetInfo对象
    pet_info_dict = response.model_dump() if hasattr(
        response, "model_dump") else response

    # 【关键】合并初始信息：如果LLM返回null但初始信息中有值，使用初始值
    if initial_pet_info:
        for key, value in initial_pet_info.items():
            # 只有当LLM返回null或空值时，才使用初始值
            if key in pet_info_dict and not pet_info_dict[key]:
                if value:  # 初始值不为空
                    pet_info_dict[key] = value
                    logger.debug(f"保留初始信息: {key}={value}")

    # 【关键】提供默认值，避免空数组和null值
    # activity_level: 默认"中等"
    if not pet_info_dict.get("activity_level") or pet_info_dict.get("activity_level") == "null":
        pet_info_dict["activity_level"] = "中等"
        logger.debug("设置默认活动水平: 中等")

    # health_conditions: 空数组或null时提供默认值
    hc = pet_info_dict.get("health_conditions")
    if not hc or len(hc) == 0:
        pet_info_dict["health_conditions"] = ["无特殊健康问题"]
        logger.debug("设置默认健康状况: 无特殊健康问题")

    # allergies: 空数组或null时提供默认值
    al = pet_info_dict.get("allergies")
    if not al or len(al) == 0:
        pet_info_dict["allergies"] = ["无已知过敏"]
        logger.debug("设置默认过敏源: 无已知过敏")

    pet_info = PetInfo(**pet_info_dict)

    logger.debug(
        f"提取的宠物信息: species={pet_info.species}, breed={pet_info.breed}, age={pet_info.age}, sex={pet_info.sex}")

    # 检查必要信息是否完整
    need_completion = not all([
        pet_info.species,
        pet_info.age or pet_info.weight,  # 至少有年龄或体重之一
    ])

    if need_completion:
        logger.warning("宠物信息不完整，需要补全")
    else:
        logger.info("宠物信息提取完成")

    elapsed_time = time.time() - start_time
    logger.info(f"【PetInfoNode】完成，耗时: {elapsed_time:.2f}秒")

    return {
        "pet": pet_info,
        "flags": {"need_pet_info_completion": "true" if need_completion else "false"}
    }
