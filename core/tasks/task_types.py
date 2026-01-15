"""
任务类型定义

定义所有AI任务的类型和状态枚举。
"""

from enum import Enum


class TaskType(str, Enum):
    """AI任务类型枚举"""
    DIAGNOSIS = "diagnosis"               # 西医诊断
    HERB_DIAGNOSIS = "herb_diagnosis"     # 中医诊断
    GRAPH_DIAGNOSIS = "graph_diagnosis"   # LangGraph智能诊断
    PET_CARE_PLAN = "pet_care_plan"       # 宠物护理计划


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"       # 等待执行
    PROCESSING = "processing" # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消


# 任务类型对应的显示名称
TASK_TYPE_NAMES = {
    TaskType.DIAGNOSIS: "西医诊断",
    TaskType.HERB_DIAGNOSIS: "中医诊断",
    TaskType.GRAPH_DIAGNOSIS: "智能诊断",
    TaskType.PET_CARE_PLAN: "宠物护理计划"
}

# 任务状态对应的显示名称
TASK_STATUS_NAMES = {
    TaskStatus.PENDING: "等待中",
    TaskStatus.PROCESSING: "处理中",
    TaskStatus.COMPLETED: "已完成",
    TaskStatus.FAILED: "失败",
    TaskStatus.CANCELLED: "已取消"
}
