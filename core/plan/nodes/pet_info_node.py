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
    logger.info("【PetInfoNode】开始提取宠物信息")

    # 获取配置
    model_name = settings.MODEL_NAME or "deepseek-ai/DeepSeek-V3"
    base_url = settings.BASE_URL or "https://api-inference.modelscope.cn/v1"
    api_key = settings.API_KEY or ""
    temperature = 0.3

    logger.debug(f"LLM配置: model={model_name}, base_url={base_url}")

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_query = state.user_query or ""

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
    system_instructions = f"""
当前时间：{current_time}
你是一位专业的宠物信息提取助手，需要从用户的查询中提取宠物的基本信息。

任务：从下面的用户查询中提取宠物信息，返回严格的JSON格式。

JSON Schema:
{{
    "name": str or null,
    "species": str or null,  # 如 "dog", "cat", "rabbit"
    "breed": str or null,    # 如 "金毛", "波斯猫"
    "age": str or null,      # 如 "3 years", "6 months"
    "weight": str or null,   # 单位kg，返回字符串格式如 "30.5"
    "sex": str or null,      # "male" or "female"
    "neutered": str or null, # 返回字符串 "true" 或 "false"
    "health_conditions": list[str],  # 如 ["糖尿病", "关节炎"]
    "allergies": list[str],          # 如 ["鸡肉", "小麦"]
    "feeding_history": str or null,
    "activity_level": str or null    # "low", "medium", or "high"
}}

要求：
- 只提取明确提到的信息，未提到的字段设为 null 或空列表
- species 和 breed 尽量用中文
- 不要编造信息
- 严格返回JSON，不要额外文本
- 不要使用Markdown代码块格式
"""

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instructions),
        HumanMessage(content=f"用户查询：{user_query}")
    ])

    # 调用LLM
    try:
        logger.debug("尝试使用结构化输出提取宠物信息")
        structured_llm = llm.with_structured_output(
            PetInfoSchema, method="json_schema")
        messages = prompt.format_messages()
        response = await structured_llm.ainvoke(messages)
        logger.info("结构化输出成功")
    except Exception as e:
        logger.warning(f"结构化输出失败: {e}，尝试普通调用")
        try:
            messages = prompt.format_messages()
            raw_response = await llm.ainvoke(messages)
            content = extract_json_from_markdown(raw_response.content)
            response_dict = json.loads(content)
            response = PetInfoSchema(**response_dict)
            logger.info("普通调用成功")
        except Exception as e2:
            logger.error(f"宠物信息提取失败: {e2}")
            return {"flags": {"need_pet_info_completion": "true"}}

    # 转换为PetInfo对象
    pet_info_dict = response.model_dump() if hasattr(
        response, "model_dump") else response
    pet_info = PetInfo(**pet_info_dict)

    logger.debug(
        f"提取的宠物信息: species={pet_info.species}, breed={pet_info.breed}, age={pet_info.age}")

    # 检查必要信息是否完整
    need_completion = not all([
        pet_info.species,
        pet_info.age or pet_info.weight,  # 至少有年龄或体重之一
    ])

    if need_completion:
        logger.warning("宠物信息不完整，需要补全")
    else:
        logger.info("宠物信息提取完成")

    return {
        "pet": pet_info,
        "flags": {"need_pet_info_completion": "true" if need_completion else "false"}
    }
