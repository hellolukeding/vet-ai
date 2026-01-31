"""
宠物护理计划路由模块

提供基于LangGraph的宠物护理计划生成接口，包括营养计划和护理计划。
"""

from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from backend.element.ele_pet_care import CreatePetCarePlanRequest, PetCarePlanResponse
from config.logger import logger
from core.plan.agent import PetCareAgent
from core.tasks import TaskType, get_task_manager

router = APIRouter()


@router.post(
    "/pet-care/plan",
    response_model=PetCarePlanResponse,
    status_code=status.HTTP_200_OK,
    summary="生成宠物护理计划",
    description="""
根据用户提供的宠物信息和需求，生成包含营养计划和护理计划的完整方案。

### 🎯 功能特性

- **智能信息提取**：自动从用户描述中提取宠物信息
- **个性化定制**：根据品种、年龄、体重、健康状况生成个性化计划
- **并行处理**：营养计划和护理计划并行生成，提高响应速度
- **科学依据**：基于兽医营养学和护理标准

### 📋 返回内容

1. **宠物信息**：提取和补全的宠物基本信息
2. **营养计划**：
   - 每日卡路里需求
   - 宏量营养素比例（蛋白质、脂肪、碳水）
   - 推荐食物列表
   - 禁忌食物列表
   - 营养补充剂建议
   - 喂养时间表
3. **护理计划**：
   - 美容护理建议
   - 医疗护理建议
   - 运动建议
   - 疫苗接种计划
   - 环境管理建议

### ⚙️ 工作流程

1. 提取和补全宠物基本信息
2. 并行生成营养计划和护理计划
3. 验证计划的一致性和安全性
4. 生成最终结构化输出

### 🔄 模式说明

- **同步模式** (`async_mode=false`)：直接返回完整结果，约2分钟
- **异步模式** (`async_mode=true`)：返回task_id，需轮询查询结果
    """.strip(),
    responses={
        200: {
            "description": "护理计划生成成功",
            "content": {
                "application/json": {
                    "example": {
                        "message": "宠物护理计划生成成功",
                        "data": {
                            "pet_info": {
                                "name": "Lucky",
                                "species": "狗",
                                "breed": "金毛",
                                "age": "3岁",
                                "weight": "30.0",
                            },
                            "nutrition_plan": {
                                "daily_calories": "1600 kcal",
                                "macro_ratio": {
                                    "protein": "30%",
                                    "fat": "20%",
                                    "carbs": "50%",
                                },
                            },
                            "care_plan": {
                                "grooming": ["每周梳理毛发2-3次"],
                                "medical": ["每年进行一次全面体检"],
                            },
                            "status": {
                                "nutrition_plan_ready": "true",
                                "care_plan_ready": "true",
                            },
                        },
                        "code": 200,
                    }
                }
            },
        },
        206: {
            "description": "部分计划生成成功（部分计划失败）",
        },
        400: {
            "description": "请求参数错误（用户查询为空）",
        },
        500: {
            "description": "服务内部错误",
        },
    },
    tags=["pet-care"],
)
async def create_pet_care_plan(
    request: CreatePetCarePlanRequest,
    async_mode: bool = Query(
        False,
        description="""
是否使用异步模式：

- **false**（默认）：同步模式，直接返回护理计划结果，响应时间约2分钟
- **true**：异步模式，返回task_id，需调用 GET `/pet-care/plan/task/{task_id}` 查询结果
        """.strip(),
    ),
) -> JSONResponse:
    logger.info(
        f"收到宠物护理计划请求: {request.user_query[:50]}..., async_mode={async_mode}"
    )

    try:
        # 检查输入是否为空
        if not request.user_query or not request.user_query.strip():
            logger.warning("用户查询为空")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "用户查询不能为空",
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                },
            )

        # 构建任务数据
        task_data = {"user_query": request.user_query}
        if request.pet_name:
            task_data["pet_name"] = request.pet_name
        if request.pet_species:
            task_data["pet_species"] = request.pet_species
        if request.pet_breed:
            task_data["pet_breed"] = request.pet_breed
        if request.pet_age:
            task_data["pet_age"] = request.pet_age
        if request.pet_weight is not None:
            task_data["pet_weight"] = request.pet_weight
        if request.pet_sex:
            task_data["pet_sex"] = request.pet_sex
        if request.pet_neutered is not None:
            task_data["pet_neutered"] = request.pet_neutered

        # 异步模式：提交任务并返回task_id
        if async_mode:
            task_manager = get_task_manager()
            task_id = task_manager.submit_task(
                TaskType.PET_CARE_PLAN, task_data, priority=0
            )
            logger.info(f"宠物护理计划任务已提交: {task_id}")
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": "宠物护理计划任务已提交，请使用task_id查询结果",
                    "data": {"task_id": task_id, "status": "pending"},
                    "code": status.HTTP_202_ACCEPTED,
                },
            )

        # 同步模式：直接执行并返回结果 (保持原有行为)
        # 构建可选的宠物初始信息
        pet_info = {}
        if request.pet_name:
            pet_info["name"] = request.pet_name
        if request.pet_species:
            pet_info["species"] = request.pet_species
        if request.pet_breed:
            pet_info["breed"] = request.pet_breed
        if request.pet_age:
            pet_info["age"] = request.pet_age
        if request.pet_weight is not None:
            pet_info["weight"] = str(request.pet_weight)  # 转换为字符串
        if request.pet_sex:
            pet_info["sex"] = request.pet_sex
        if request.pet_neutered is not None:
            pet_info["neutered"] = (
                "true" if request.pet_neutered else "false"
            )  # 转换为字符串

        logger.debug(f"初始宠物信息: {pet_info}")

        # 创建代理并执行工作流
        agent = PetCareAgent()
        result = await agent.run(
            user_query=request.user_query, pet_info=pet_info if pet_info else None
        )

        logger.info("宠物护理计划生成完成")

        # 构建响应数据
        response_data = {
            "pet_info": {
                "name": result.pet.name,
                "species": result.pet.species,
                "breed": result.pet.breed,
                "age": result.pet.age,
                "weight": result.pet.weight,
                "sex": result.pet.sex,
                "neutered": result.pet.neutered,
                "health_conditions": result.pet.health_conditions,
                "allergies": result.pet.allergies,
                "activity_level": result.pet.activity_level,
            },
            "nutrition_plan": {
                "daily_calories": result.nutrition_plan.daily_calories,
                "macro_ratio": result.nutrition_plan.macro_ratio,
                "recommended_foods": result.nutrition_plan.recommended_foods,
                "avoid_foods": result.nutrition_plan.avoid_foods,
                "supplements": result.nutrition_plan.supplements,
                "feeding_schedule": result.nutrition_plan.feeding_schedule,
            },
            "care_plan": {
                "grooming": result.care_plan.grooming,
                "medical": result.care_plan.medical,
                "exercise": result.care_plan.exercise,
                "vaccination": result.care_plan.vaccination,
                "environment": result.care_plan.environment,
            },
            "validation": {
                "risk_analysis": result.reasoning.risk_analysis,
                "contradictions": result.reasoning.contradictions,
            },
            "status": {
                "nutrition_plan_ready": result.flags.nutrition_plan_ready,
                "care_plan_ready": result.flags.care_plan_ready,
                "final_output_ready": result.flags.final_output_ready,
            },
        }

        # 检查计划是否全部完成
        nutrition_ready = result.flags.nutrition_plan_ready == "true"
        care_ready = result.flags.care_plan_ready == "true"

        # 分析失败原因并提供详细信息
        failure_reasons = []
        if not nutrition_ready:
            if result.reasoning.nutrition_agent_notes:
                failure_reasons.append(
                    f"营养计划失败: {result.reasoning.nutrition_agent_notes}"
                )
            else:
                failure_reasons.append("营养计划生成失败（原因未知）")
        if not care_ready:
            if result.reasoning.care_agent_notes:
                failure_reasons.append(
                    f"护理计划失败: {result.reasoning.care_agent_notes}"
                )
            else:
                failure_reasons.append("护理计划生成失败（原因未知）")

        if not nutrition_ready or not care_ready:
            logger.warning(f"部分计划未完成: {', '.join(failure_reasons)}")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": f"护理计划部分生成成功。{' '.join(failure_reasons)}",
                    "data": response_data,
                    "code": status.HTTP_206_PARTIAL_CONTENT,
                    "details": {
                        "nutrition_ready": nutrition_ready,
                        "care_ready": care_ready,
                        "failure_reasons": failure_reasons,
                    },
                },
            )

        logger.info("所有计划生成成功")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "宠物护理计划生成成功",
                "data": response_data,
                "code": status.HTTP_200_OK,
            },
        )

    except Exception as e:
        logger.error(f"生成宠物护理计划失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": f"护理计划生成服务暂时不可用: {str(e)}",
                "data": None,
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
        )


@router.get(
    "/pet-care/health",
    status_code=status.HTTP_200_OK,
    summary="宠物护理服务健康检查",
    description="""
检查宠物护理计划服务的运行状态。

### 📊 返回信息

- **message**：服务状态描述
- **code**：HTTP状态码
- **service**：服务标识
- **version**：服务版本号
    """.strip(),
    responses={
        200: {
            "description": "服务运行正常",
            "content": {
                "application/json": {
                    "example": {
                        "message": "宠物护理计划服务运行正常",
                        "code": 200,
                        "service": "pet-care-plan",
                        "version": "1.0.0",
                    }
                }
            },
        }
    },
    tags=["pet-care"],
)
async def health_check() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "宠物护理计划服务运行正常",
            "code": status.HTTP_200_OK,
            "service": "pet-care-plan",
            "version": "1.0.0",
        },
    )


@router.get(
    "/pet-care/plan/task/{task_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="查询宠物护理计划任务状态",
    description="""
查询异步任务的执行状态和结果（仅用于异步模式）。

### 🔄 任务状态

- **pending**：任务排队中，等待执行
- **processing**：任务处理中，包含进度信息
- **completed**：任务已完成，包含完整的护理计划结果
- **failed**：任务执行失败，包含错误信息

### 📝 使用流程

1. 调用 POST `/pet-care/plan?async_mode=true` 提交任务
2. 获取返回的 `task_id`
3. 调用此接口查询任务状态
4. 如果状态为 `processing`，继续轮询
5. 如果状态为 `completed`，获取护理计划结果
    """.strip(),
    responses={
        200: {
            "description": "查询成功",
            "content": {
                "application/json": {
                    "examples": {
                        "completed": {
                            "summary": "任务完成",
                            "value": {
                                "message": "宠物护理计划生成成功",
                                "data": {
                                    "pet_info": {"name": "Lucky"},
                                    "nutrition_plan": {"daily_calories": "1600 kcal"},
                                    "care_plan": {"grooming": ["每周梳理毛发"]},
                                },
                                "code": 200,
                            },
                        },
                        "processing": {
                            "summary": "处理中",
                            "value": {
                                "message": "正在处理: 生成营养计划",
                                "data": {
                                    "task_id": "abc123",
                                    "status": "processing",
                                    "progress": {
                                        "stage": "生成营养计划",
                                        "percentage": 50,
                                    },
                                },
                                "code": 200,
                            },
                        },
                        "pending": {
                            "summary": "等待中",
                            "value": {
                                "message": "任务排队中",
                                "data": {"task_id": "abc123", "status": "pending"},
                                "code": 200,
                            },
                        },
                    }
                }
            },
        },
        404: {
            "description": "任务不存在或已过期",
        },
    },
    tags=["pet-care"],
)
async def get_pet_care_plan_task_status(task_id: str) -> JSONResponse:
    task_manager = get_task_manager()
    status_info = task_manager.get_task_status(task_id)

    if not status_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": "任务不存在或已过期",
                "data": None,
                "code": status.HTTP_404_NOT_FOUND,
            },
        )

    task_status = status_info["status"]

    # 任务完成
    if task_status == "completed":
        result = task_manager.get_task_result(task_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "宠物护理计划生成成功",
                "data": result,
                "code": status.HTTP_200_OK,
            },
        )

    # 任务失败
    elif task_status == "failed":
        result = task_manager.get_task_result(task_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": result.get("error", "宠物护理计划任务执行失败"),
                "data": None,
                "code": status.HTTP_200_OK,
            },
        )

    # 任务处理中
    elif task_status == "processing":
        progress = status_info.get("progress", {})
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"正在处理: {progress.get('stage', '生成护理计划中')}",
                "data": {
                    "task_id": task_id,
                    "status": "processing",
                    "progress": progress,
                },
                "code": status.HTTP_200_OK,
            },
        )

    # 任务等待中
    else:  # pending
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "任务排队中",
                "data": {"task_id": task_id, "status": "pending"},
                "code": status.HTTP_200_OK,
            },
        )


@router.delete(
    "/pet-care/plan/task/{task_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="取消宠物护理计划任务",
    description="""
取消正在执行或排队中的宠物护理计划任务（仅用于异步模式）。

### ⚠️ 注意事项

- 只能取消状态为 `pending` 或 `processing` 的任务
- 已完成（`completed`）或失败（`failed`）的任务无法取消
- 取消操作是立即执行的

### 📋 返回结果

- **cancelled=true**：任务成功取消
- **cancelled=false**：任务无法取消（可能已完成或不存在）
    """.strip(),
    responses={
        200: {
            "description": "取消请求处理完成",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "取消成功",
                            "value": {
                                "message": "任务已取消",
                                "data": {"task_id": "abc123", "cancelled": True},
                                "code": 200,
                            },
                        },
                        "failed": {
                            "summary": "无法取消",
                            "value": {
                                "message": "任务无法取消（可能已完成或不存在）",
                                "data": {"task_id": "abc123", "cancelled": False},
                                "code": 200,
                            },
                        },
                    }
                }
            },
        }
    },
    tags=["pet-care"],
)
async def cancel_pet_care_plan_task(task_id: str) -> JSONResponse:
    task_manager = get_task_manager()
    success = task_manager.cancel_task(task_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "任务已取消"
            if success
            else "任务无法取消（可能已完成或不存在）",
            "data": {"task_id": task_id, "cancelled": success},
            "code": status.HTTP_200_OK,
        },
    )
