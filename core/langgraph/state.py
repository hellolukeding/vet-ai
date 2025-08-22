from langgraph.graph import MessagesState
from pydantic import BaseModel, Field


class DiagnosisItem(BaseModel):
    symptom: str
    reason: str
    probability: float


class MedicationItem(BaseModel):
    symptom: str
    drug_name: str
    dosage: str  # 可以是 "10mg/kg" 这种格式
    frequency: str = ""  # 可选字段


class VetAgentState(MessagesState):
    description: str = ""  # 宠物症状的一句话描述
    diagnosis: list[DiagnosisItem] = []  # 宠物的诊断列表，包括症状名称和依据和可能性p
    medications: list[MedicationItem] = []  # 宠物的用药列表，包括症状、药品名称和剂量


__all__ = [
    "DiagnosisItem",
    "MedicationItem",
    "VetAgentState"
]
