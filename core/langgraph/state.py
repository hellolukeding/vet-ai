from langgraph.graph import MessagesState
from pydantic import BaseModel


class DiagnosisItem(BaseModel):
    symptom: str
    reason: str
    probability: float


class MedicationItem(BaseModel):
    symptom: str
    drug_name: str
    dosage: str  # 可以是 "10mg/kg" 这种格式
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
