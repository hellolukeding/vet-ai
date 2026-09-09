from langgraph.graph import MessagesState
from pydantic import BaseModel, Field


class DiagnosisItem(BaseModel):
    symptom: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    probability: float = Field(ge=0, le=1)


class MedicationItem(BaseModel):
    symptom: str = Field(min_length=1)
    drug_name: str = Field(min_length=1)
    dosage: str = Field(min_length=1)  # 可以是 "10mg/kg" 这种格式
    frequency: str = ""  # 可选字段
    safety_warning: str = ""  # 该药物的安全警告


class LiteratureItem(BaseModel):
    """文献搜索结果项"""

    title: str
    snippet: str
    url: str
    content: str = ""  # 网页完整内容（可选）


class VetAgentState(MessagesState):
    description: str = ""  # 宠物症状的一句话描述
    literature: list[LiteratureItem] = []  # 文献搜索结果
    diagnosis: list[DiagnosisItem] = []  # 宠物的诊断列表，包括症状名称和依据和可能性p
    medications: list[MedicationItem] = []  # 宠物的用药列表，包括症状、药品名称和剂量


__all__ = ["DiagnosisItem", "MedicationItem", "LiteratureItem", "VetAgentState"]
