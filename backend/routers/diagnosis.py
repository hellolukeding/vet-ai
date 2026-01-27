from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from backend.element.ele_diagnosis import CreateDiagnosisRequest
from config.logger import logger
from core.ai_diagnosis.diagnosis import Diagnosis
from core.ai_diagnosis.herb_diagnosis import HerbDiagnosis
from core.tasks import TaskType, get_task_manager

router = APIRouter()

# /*--------------------------------------- api ------------------------------------------*/


@router.post(
    "/diagnosis",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="宠物疾病诊断（基础版）",
    description="""
根据宠物症状描述生成疾病诊断和用药建议。

### 🩺 功能说明

基于症状描述进行快速诊断，适用于常见疾病。

### 📋 返回内容

- **疾病列表**：可能的疾病诊断结果
- **症状说明**：每个疾病的典型症状描述
- **治疗建议**：推荐的治疗方案和药物

### 🔄 模式说明

- **同步模式** (`async_mode=false`)：直接返回诊断结果
- **异步模式** (`async_mode=true`)：返回task_id，需轮询查询结果

### ⚡ 性能

- 同步模式：通常 5-15 秒
- 适合：常见疾病快速诊断
    """.strip(),
    responses={
        200: {
            "description": "诊断成功",
            "content": {
                "application/json": {
                    "example": {
                        "message": "诊断成功",
                        "data": [
                            {
                                "disease": "犬细小病毒感染",
                                "description": "这是一种高度传染性的病毒性疾病...",
                                "symptoms": ["呕吐", "腹泻", "食欲不振"],
                                "treatment": "输液治疗, 抗病毒药物..."
                            }
                        ],
                        "code": 200
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误（症状描述为空）",
        }
    },
    tags=["diagnosis"],
)
async def create_diagnosis(
    diagnosis_data: CreateDiagnosisRequest,
    async_mode: bool = Query(
        False,
        description="是否使用异步模式：false=同步直接返回结果，true=异步返回task_id"
    ),
) -> JSONResponse:
    logger.info(f"开始处理诊断请求: {diagnosis_data.description}, async_mode={async_mode}")

    try:
        # 检查输入是否为空
        if not diagnosis_data.description or not diagnosis_data.description.strip():
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
                TaskType.DIAGNOSIS,
                {"symptoms": diagnosis_data.description},
                priority=0
            )
            logger.info(f"诊断任务已提交: {task_id}")
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": "诊断任务已提交，请使用task_id查询结果",
                    "data": {
                        "task_id": task_id,
                        "status": "pending"
                    },
                    "code": status.HTTP_202_ACCEPTED
                }
            )

        # 同步模式：直接执行并返回结果 (保持原有行为)
        diagnosis = Diagnosis()
        result = diagnosis.diagnosis(diagnosis_data.description)
        logger.info(f"result: {result}")

        # 确保返回的数据格式正确
        if not isinstance(result, list):
            logger.warning(f"诊断结果不是列表格式: {type(result)}")
            result = []

        # 如果结果为空，返回友好提示
        if len(result) == 0:
            logger.info("未获得有效诊断结果")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "未能根据提供的症状生成诊断结果，请提供更详细的症状描述",
                    "data": [],
                    "code": status.HTTP_200_OK
                }
            )

        logger.info(f"诊断完成，返回 {len(result)} 个诊断结果")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "诊断成功",
                "data": result,
                "code": status.HTTP_200_OK
            }
        )
    except Exception as e:
        error_msg = repr(e)
        logger.error("诊断失败: %s", error_msg, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "诊断服务暂时不可用，请稍后重试",
                "data": [],
                "code": status.HTTP_200_OK
            }
        )


@router.get(
    "/diagnosis/task/{task_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="查询诊断任务状态",
    description="""
查询异步诊断任务的执行状态和结果。

### 🔄 任务状态

- **pending**：任务排队中
- **processing**：任务处理中
- **completed**：任务完成，包含诊断结果
- **failed**：任务失败
    """.strip(),
    tags=["diagnosis"],
)
async def get_diagnosis_task_status(
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
                "message": "诊断成功",
                "data": result.get("diagnoses", []),
                "code": status.HTTP_200_OK
            }
        )

    # 任务失败
    elif task_status == "failed":
        result = task_manager.get_task_result(task_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": result.get("error", "诊断任务执行失败"),
                "data": [],
                "code": status.HTTP_200_OK
            }
        )

    # 任务处理中
    elif task_status == "processing":
        progress = status_info.get("progress", {})
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"正在处理: {progress.get('stage', '诊断中')}",
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
    "/diagnosis/task/{task_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="取消诊断任务",
    description="取消正在执行或排队中的诊断任务",
    tags=["diagnosis"],
)
async def cancel_diagnosis_task(
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


@router.post(
    "/vet/herb",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="宠物中医诊断（草本治疗）",
    description="""
根据宠物症状进行中医辨证论治，提供草本治疗方案。

### 🌿 功能说明

基于传统中医理论进行诊断和治疗：
- **辨证论治**：根据症状进行中医辨证
- **草本处方**：推荐天然草本治疗方案
- **整体调理**：注重身体整体平衡

### 📋 返回内容

- **中医诊断**：证型判断（如风寒感冒、脾胃虚弱等）
- **草本处方**：推荐的中药和草本配方
- **用法用量**：详细的使用说明
- **注意事项**：服药禁忌和注意事项

### 🔄 模式说明

- **同步模式** (`async_mode=false`)：直接返回诊断结果
- **异步模式** (`async_mode=true`)：返回task_id，需轮询查询结果
    """.strip(),
    responses={
        200: {
            "description": "中医诊断成功",
        },
        400: {
            "description": "请求参数错误",
        }
    },
    tags=["diagnosis"],
)
async def create_herb_diagnosis(
    diagnosis_data: CreateDiagnosisRequest,
    async_mode: bool = Query(False, description="是否使用异步模式"),
) -> JSONResponse:
    logger.info(f"开始处理中医诊断请求: {diagnosis_data.description}, async_mode={async_mode}")

    try:
        # 检查输入是否为空
        if not diagnosis_data.description or not diagnosis_data.description.strip():
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
                TaskType.HERB_DIAGNOSIS,
                {"symptoms": diagnosis_data.description},
                priority=0
            )
            logger.info(f"中医诊断任务已提交: {task_id}")
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": "中医诊断任务已提交，请使用task_id查询结果",
                    "data": {
                        "task_id": task_id,
                        "status": "pending"
                    },
                    "code": status.HTTP_202_ACCEPTED
                }
            )

        # 同步模式：直接执行并返回结果 (保持原有行为)
        diagnosis = HerbDiagnosis()
        result = diagnosis.diagnosis(diagnosis_data.description)
        logger.info(f"result: {result}")

        # 确保返回的数据格式正确
        if not isinstance(result, list):
            logger.warning(f"诊断结果不是列表格式: {type(result)}")
            result = []

        # 如果结果为空，返回友好提示
        if len(result) == 0:
            logger.info("未获得有效诊断结果")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "未能根据提供的症状生成中医诊断结果，请提供更详细的症状描述",
                    "data": [],
                    "code": status.HTTP_200_OK
                }
            )

        logger.info(f"中医诊断完成，返回 {len(result)} 个诊断结果")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "中医诊断成功",
                "data": result,
                "code": status.HTTP_200_OK
            }
        )
    except Exception as e:
        error_msg = repr(e)
        logger.error("中医诊断失败: %s", error_msg, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "中医诊断服务暂时不可用，请稍后重试",
                "data": [],
                "code": status.HTTP_200_OK
            }
        )


@router.get(
    "/vet/herb/task/{task_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="查询中医诊断任务状态",
    description="查询异步中医诊断任务的执行状态和结果",
    tags=["diagnosis"],
)
async def get_herb_diagnosis_task_status(
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
                "message": "中医诊断成功",
                "data": result.get("diagnoses", []),
                "code": status.HTTP_200_OK
            }
        )

    # 任务失败
    elif task_status == "failed":
        result = task_manager.get_task_result(task_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": result.get("error", "中医诊断任务执行失败"),
                "data": [],
                "code": status.HTTP_200_OK
            }
        )

    # 任务处理中
    elif task_status == "processing":
        progress = status_info.get("progress", {})
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"正在处理: {progress.get('stage', '中医诊断中')}",
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
    "/vet/herb/task/{task_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="取消中医诊断任务",
    description="取消正在执行或排队中的中医诊断任务",
    tags=["diagnosis"],
)
async def cancel_herb_diagnosis_task(
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
