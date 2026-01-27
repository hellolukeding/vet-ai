from fastapi import APIRouter, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.langgraph.agent import graph
from core.langgraph.state import VetAgentState
from core.tasks import TaskType, get_task_manager
from config.logger import logger

router = APIRouter()

# 请求体


class DiagnosisRequest(BaseModel):
    description: str


# @app.post("/vet/diagnose")
@router.post(
    "/vet/diagnose",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="LangGraph智能诊断（高级版）",
    description="""
基于LangGraph工作流的先进智能诊断系统，提供多步推理和增强准确性。

### 🧠 功能特性

- **多步推理**：通过状态机实现复杂诊断流程
- **工作流管理**：支持诊断过程的可视化和管理
- **增强准确性**：通过多轮对话和验证提高诊断准确率
- **状态追踪**：实时追踪诊断过程的每个步骤

### 🎯 适用场景

- 复杂疑难病例
- 需要多系统分析的综合诊断
- 需要详细推理过程的诊断

### 📋 返回内容

- **description**：症状描述
- **diagnosis**：诊断结果列表（包含疾病名称、症状、治疗方案）
- **medications**：推荐药物列表

### 🔄 模式说明

- **同步模式** (`async_mode=false`)：直接返回诊断结果
- **异步模式** (`async_mode=true`)：返回task_id，需轮询查询结果

### ⚡ 性能

- 同步模式：通常 30-60 秒（复杂病例可能更长）
- 异步模式：适合复杂诊断任务
    """.strip(),
    responses={
        200: {
            "description": "智能诊断成功",
            "content": {
                "application/json": {
                    "example": {
                        "message": "智能诊断成功",
                        "data": {
                            "description": "金毛犬Lucky呕吐、腹泻",
                            "diagnosis": [
                                {
                                    "name": "急性胃肠炎",
                                    "symptoms": ["呕吐", "腹泻", "腹痛"],
                                    "description": "胃和肠道的急性炎症..."
                                }
                            ],
                            "medications": [
                                {
                                    "name": "止吐药",
                                    "dosage": "根据体重",
                                    "usage": "口服，每日2次"
                                }
                            ]
                        },
                        "code": 200
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误",
        }
    },
    tags=["graph"],
)
async def diagnose(
    request: DiagnosisRequest,
    async_mode: bool = Query(False, description="是否使用异步模式"),
) -> JSONResponse:
    logger.info(f"开始处理LangGraph智能诊断请求: {request.description}, async_mode={async_mode}")

    try:
        # 检查输入是否为空
        if not request.description or not request.description.strip():
            logger.warning("诊断描述为空")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "诊断描述不能为空",
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST
                }
            )

        # 异步模式：提交任务并返回task_id
        if async_mode:
            task_manager = get_task_manager()
            task_id = task_manager.submit_task(
                TaskType.GRAPH_DIAGNOSIS,
                {"query": request.description},
                priority=0
            )
            logger.info(f"LangGraph智能诊断任务已提交: {task_id}")
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": "智能诊断任务已提交，请使用task_id查询结果",
                    "data": {
                        "task_id": task_id,
                        "status": "pending"
                    },
                    "code": status.HTTP_202_ACCEPTED
                }
            )

        # 同步模式：直接执行并返回结果 (保持原有行为)
        state = VetAgentState(description=request.description)

        # 运行 Graph
        final_state = await graph.ainvoke(state)

        # 返回最终结果
        # 处理graph.ainvoke可能返回字典而不是对象的情况
        description = final_state.get("description") if isinstance(final_state, dict) else getattr(final_state, "description", "")
        diagnosis = final_state.get("diagnosis") if isinstance(final_state, dict) else getattr(final_state, "diagnosis", [])
        medications = final_state.get("medications") if isinstance(final_state, dict) else getattr(final_state, "medications", [])

        logger.info(f"LangGraph智能诊断完成，返回 {len(diagnosis)} 个诊断结果")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "智能诊断成功",
                "data": {
                    "description": description,
                    "diagnosis": [d.dict() if hasattr(d, 'dict') else d for d in diagnosis],
                    "medications": [m.dict() if hasattr(m, 'dict') else m for m in medications],
                },
                "code": status.HTTP_200_OK
            }
        )
    except Exception as e:
        error_msg = repr(e)
        logger.error("LangGraph智能诊断失败: %s", error_msg, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "智能诊断服务暂时不可用，请稍后重试",
                "data": None,
                "code": status.HTTP_200_OK
            }
        )


@router.get(
    "/vet/diagnose/task/{task_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="查询LangGraph智能诊断任务状态",
    description="""
查询LangGraph智能诊断任务的执行状态和结果。

### 🔄 任务状态

- **pending**：任务排队中
- **processing**：任务处理中（包含工作流进度）
- **completed**：任务完成，包含诊断结果
- **failed**：任务失败
    """.strip(),
    tags=["graph"],
)
async def get_graph_diagnosis_task_status(
    task_id: str
) -> JSONResponse:
    task_manager = get_task_manager()
    status_info = task_manager.get_task_status(task_id)

    if not status_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": "任务不存在或已过期",
                "data": None,
                "code": status.HTTP_404_NOT_FOUND
            }
        )

    task_status = status_info["status"]

    # 任务完成
    if task_status == "completed":
        result = task_manager.get_task_result(task_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "智能诊断成功",
                "data": result,
                "code": status.HTTP_200_OK
            }
        )

    # 任务失败
    elif task_status == "failed":
        result = task_manager.get_task_result(task_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": result.get("error", "智能诊断任务执行失败"),
                "data": None,
                "code": status.HTTP_200_OK
            }
        )

    # 任务处理中
    elif task_status == "processing":
        progress = status_info.get("progress", {})
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"正在处理: {progress.get('stage', '智能诊断中')}",
                "data": {
                    "task_id": task_id,
                    "status": "processing",
                    "progress": progress
                },
                "code": status.HTTP_200_OK
            }
        )

    # 任务等待中
    else:  # pending
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "任务排队中",
                "data": {
                    "task_id": task_id,
                    "status": "pending"
                },
                "code": status.HTTP_200_OK
            }
        )


@router.delete(
    "/vet/diagnose/task/{task_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="取消LangGraph智能诊断任务",
    description="取消正在执行或排队中的LangGraph智能诊断任务",
    tags=["graph"],
)
async def cancel_graph_diagnosis_task(
    task_id: str
) -> JSONResponse:
    task_manager = get_task_manager()
    success = task_manager.cancel_task(task_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "任务已取消" if success else "任务无法取消（可能已完成或不存在）",
            "data": {"task_id": task_id, "cancelled": success},
            "code": status.HTTP_200_OK
        }
    )