"""
宠物护理计划状态管理模块

该模块定义了LangGraph工作流中使用的状态类，用于管理宠物信息、营养计划、护理计划等数据。
"""

from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel


class PetInfo(BaseModel):
    """
    宠物基本信息类

    存储宠物的基本属性和健康相关信息，用于后续的营养和护理计划制定。
    """
    name: Optional[str] = None  # 宠物名称
    species: Optional[str] = None  # 物种类型，如: dog/cat/rabbit等
    breed: Optional[str] = None  # 品种，如: 金毛、波斯猫等
    age: Optional[str] = None  # 年龄，格式如: "3 years", "6 months"
    weight: Optional[float] = None  # 体重（单位：kg）
    sex: Optional[str] = None  # 性别：male/female
    neutered: Optional[bool] = None  # 是否绝育

    health_conditions: List[str] = []  # 健康状况列表，如：糖尿病、关节炎等
    allergies: List[str] = []  # 过敏源列表，如：鸡肉、小麦等
    feeding_history: Optional[str] = None  # 喂养历史描述
    activity_level: Optional[str] = None  # 活动水平: low/medium/high


class NutritionPlan(BaseModel):
    """
    宠物营养计划类

    包含宠物的每日营养需求、推荐食物、禁忌食物、补充剂和喂养时间表。
    由营养代理(nutrition agent)生成和维护。
    """
    daily_calories: Optional[float] = None  # 每日卡路里需求（单位：kcal）
    macro_ratio: Dict[str, float] = {}  # 宏量营养素比例，键为: protein/fat/carbs，值为百分比
    recommended_foods: List[str] = []  # 推荐食物列表
    avoid_foods: List[str] = []  # 应避免的食物列表（基于过敏或健康状况）
    supplements: List[str] = []  # 推荐的营养补充剂列表
    feeding_schedule: List[str] = []  # 喂养时间表，如: ["早上8点", "下午6点"]


class CarePlan(BaseModel):
    """
    宠物护理计划类

    包含宠物的日常护理、医疗、运动、疫苗接种和环境管理建议。
    由护理代理(care agent)生成和维护。
    """
    grooming: List[str] = []  # 美容护理建议列表，如：刷牙、梳毛、洗澡频率等
    medical: List[str] = []  # 医疗护理建议列表，如：定期体检、用药提醒等
    exercise: List[str] = []  # 运动建议列表，如：每日散步时长、运动类型等
    vaccination: List[str] = []  # 疫苗接种计划列表
    environment: List[str] = []  # 环境管理建议列表，如：温度控制、安全措施等


class IntermediateReasoning(BaseModel):
    """
    中间推理过程记录类

    记录各个代理(agent)的推理笔记、风险分析和潜在冲突，用于调试和审计。
    """
    nutrition_agent_notes: Optional[str] = None  # 营养代理的推理笔记和决策依据
    care_agent_notes: Optional[str] = None  # 护理代理的推理笔记和决策依据
    risk_analysis: Optional[str] = None  # 风险评估分析结果
    contradictions: List[str] = []  # 检测到的冲突列表，如营养和护理建议之间的矛盾


class WorkflowFlags(BaseModel):
    """
    工作流标志类

    控制LangGraph工作流的执行流程，标记各个阶段的完成状态。
    """
    need_pet_info_completion: bool = False  # 是否需要补全宠物信息
    nutrition_plan_ready: bool = False  # 营养计划是否已准备就绪
    care_plan_ready: bool = False  # 护理计划是否已准备就绪
    final_output_ready: bool = False  # 最终输出是否已准备就绪


# Reducer functions for handling concurrent updates in parallel nodes
def merge_reasoning_dicts(left, right):
    """
    合并推理字典的reducer函数

    用于处理并行节点同时更新reasoning字段的情况。
    每个节点可以更新自己的字段，不会互相覆盖。

    Args:
        left: 当前的推理对象或字典
        right: 要更新的推理字典

    Returns:
        IntermediateReasoning: 合并后的推理对象
    """
    # 将left转换为字典
    if isinstance(left, IntermediateReasoning):
        left_dict = left.model_dump()
    elif isinstance(left, dict):
        left_dict = left.copy()
    else:
        left_dict = {}

    # 合并right
    if isinstance(right, dict):
        left_dict.update(right)
    elif isinstance(right, IntermediateReasoning):
        left_dict.update(right.model_dump())

    return IntermediateReasoning(**left_dict)


def merge_flags_dicts(left, right):
    """
    合并工作流标志字典的reducer函数

    用于处理并行节点同时更新flags字段的情况。

    Args:
        left: 当前的标志对象或字典
        right: 要更新的标志字典

    Returns:
        WorkflowFlags: 合并后的标志对象
    """
    # 将left转换为字典
    if isinstance(left, WorkflowFlags):
        left_dict = left.model_dump()
    elif isinstance(left, dict):
        left_dict = left.copy()
    else:
        left_dict = {}

    # 合并right
    if isinstance(right, dict):
        left_dict.update(right)
    elif isinstance(right, WorkflowFlags):
        left_dict.update(right.model_dump())

    return WorkflowFlags(**left_dict)


class State(BaseModel):
    """
    LangGraph工作流全局状态类

    这是整个宠物护理计划生成工作流的核心状态容器，贯穿所有节点。
    包含用户查询、宠物信息、计划、推理过程、工作流标志和消息历史。

    Attributes:
        user_query: 用户的原始查询文本
        pet: 宠物基本信息对象
        nutrition_plan: 生成的营养计划对象
        care_plan: 生成的护理计划对象
        reasoning: 中间推理过程记录
        flags: 工作流执行标志
        messages: LangGraph消息存储，记录各节点之间的消息传递
    """
    user_query: Optional[str] = None  # 用户的原始查询输入
    pet: PetInfo = PetInfo()  # 宠物信息实例

    nutrition_plan: NutritionPlan = NutritionPlan()  # 营养计划实例
    care_plan: CarePlan = CarePlan()  # 护理计划实例

    # 使用Annotated和reducer来处理并行节点的并发更新
    reasoning: Annotated[IntermediateReasoning,
                         merge_reasoning_dicts] = IntermediateReasoning()  # 推理过程记录实例
    flags: Annotated[WorkflowFlags,
                     merge_flags_dicts] = WorkflowFlags()  # 工作流标志实例

    messages: List[Dict[str, Any]] = []  # LangGraph消息存储列表，用于节点间通信

    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True  # 允许任意类型

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "State":
        """
        从字典创建State对象，正确处理嵌套的Pydantic模型

        Args:
            data: 包含状态数据的字典（通常来自LangGraph）

        Returns:
            State: 正确构建的State对象
        """
        # 创建副本以避免修改原始数据
        processed_data = data.copy()

        # 处理pet字段
        if "pet" in processed_data and isinstance(processed_data["pet"], dict):
            processed_data["pet"] = PetInfo(**processed_data["pet"])

        # 处理nutrition_plan字段
        if "nutrition_plan" in processed_data and isinstance(processed_data["nutrition_plan"], dict):
            processed_data["nutrition_plan"] = NutritionPlan(
                **processed_data["nutrition_plan"])

        # 处理care_plan字段
        if "care_plan" in processed_data and isinstance(processed_data["care_plan"], dict):
            processed_data["care_plan"] = CarePlan(
                **processed_data["care_plan"])

        # 处理reasoning字段
        if "reasoning" in processed_data and isinstance(processed_data["reasoning"], dict):
            processed_data["reasoning"] = IntermediateReasoning(
                **processed_data["reasoning"])

        # 处理flags字段
        if "flags" in processed_data and isinstance(processed_data["flags"], dict):
            processed_data["flags"] = WorkflowFlags(**processed_data["flags"])

        return cls(**processed_data)

    def model_copy(self, update: Dict[str, Any] = None, deep: bool = False):
        """
        支持部分更新的复制方法

        LangGraph需要此方法来处理节点返回的部分状态更新
        """
        if update is None:
            return super().model_copy(deep=deep)

        # 深度复制当前状态
        new_state = super().model_copy(deep=True)

        # 应用更新
        for key, value in update.items():
            if hasattr(new_state, key):
                current_value = getattr(new_state, key)

                # 对于嵌套的Pydantic模型，进行合并更新
                if isinstance(current_value, BaseModel) and isinstance(value, dict):
                    # 获取当前值的字典表示
                    current_dict = current_value.model_dump()
                    # 更新字典
                    current_dict.update(value)
                    # 创建新的模型实例
                    model_class = type(current_value)
                    setattr(new_state, key, model_class(**current_dict))
                elif isinstance(current_value, BaseModel) and isinstance(value, BaseModel):
                    # 如果传入的是Pydantic模型，直接替换
                    setattr(new_state, key, value)
                else:
                    # 其他类型直接设置
                    setattr(new_state, key, value)

        return new_state
