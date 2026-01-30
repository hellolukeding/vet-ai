"""
中医诊断专用状态定义
"""
from langgraph.graph import MessagesState
from pydantic import BaseModel, Field


class TCMZhengmingItem(BaseModel):
    """中医证型诊断项"""
    zhengming: str = Field(..., description="中医证名（如脾胃虚弱、风寒感冒等）")
    description: str = Field(..., description="病理分析描述")
    probability: float = Field(..., description="诊断概率 0-1")
    therapy: str = Field(..., description="治法")


class HerbalPrescriptionItem(BaseModel):
    """中药方剂项"""
    zhengming: str = Field(..., description="对应的中医证名")
    prescription_type: str = Field(..., description="方剂类型（基础方/加减方/急救方）")
    prescription_name: str = Field(..., description="方剂名称（如参苓白术散、银翘散等）")
    composition: str = Field(..., description="方剂组成（药物和剂量）")
    usage: str = Field(..., description="用法用量")


class TCMNursingItem(BaseModel):
    """中医护理建议项"""
    category: str = Field(..., description="护理类别（基础护理/继续观察/建议就医）")
    content: str = Field(..., description="护理内容")


class TCMRefItem(BaseModel):
    """中医文献参考项"""
    title: str
    content: str = ""


class TCAgentState(MessagesState):
    """中医诊断Agent状态"""
    description: str = ""  # 症状描述
    literature: list[TCMRefItem] = []  # 中医文献参考
    zhengming: list[TCMZhengmingItem] = []  # 证型诊断列表
    prescriptions: list[HerbalPrescriptionItem] = []  # 方剂建议列表
    nursing: list[TCMNursingItem] = []  # 护理建议


__all__ = [
    "TCMZhengmingItem",
    "HerbalPrescriptionItem",
    "TCMNursingItem",
    "TCMRefItem",
    "TCAgentState"
]
