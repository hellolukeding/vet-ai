from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from core.langgraph.agent import graph
from core.langgraph.state import VetAgentState

router = APIRouter()

# 请求体


class DiagnosisRequest(BaseModel):
    description: str


# @app.post("/vet/diagnose")
@router.post("/vet/diagnose", response_model=dict, status_code=status.HTTP_200_OK)
async def diagnose(request: DiagnosisRequest):
    # 初始化 state
    state = VetAgentState(description=request.description)

    # 运行 Graph
    final_state = await graph.ainvoke(state)

    # 返回最终结果
    # 处理graph.ainvoke可能返回字典而不是对象的情况
    description = final_state.get("description") if isinstance(final_state, dict) else getattr(final_state, "description", "")
    diagnosis = final_state.get("diagnosis") if isinstance(final_state, dict) else getattr(final_state, "diagnosis", [])
    medications = final_state.get("medications") if isinstance(final_state, dict) else getattr(final_state, "medications", [])
    
    return {
        "description": description,
        "diagnosis": [d.dict() if hasattr(d, 'dict') else d for d in diagnosis],
        "medications": [m.dict() if hasattr(m, 'dict') else m for m in medications],
    }