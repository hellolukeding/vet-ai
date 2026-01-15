"""
宠物护理计划路由模块

提供基于LangGraph的宠物护理计划生成接口，包括营养计划和护理计划。
"""

from typing import Any, Dict

from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from backend.element.ele_pet_care import (CreatePetCarePlanRequest,
                                          PetCarePlanResponse)
from config.logger import logger
from core.plan.agent import PetCareAgent
from core.tasks import TaskType, get_task_manager

router = APIRouter()


@router.post("/pet-care/plan", response_model=PetCarePlanResponse, status_code=status.HTTP_200_OK)
async def create_pet_care_plan(
    request: CreatePetCarePlanRequest,
    async_mode: bool = Query(False, description="是否使用异步模式")
) -> JSONResponse:
    """
    创建宠物护理计划

    根据用户提供的宠物信息和需求，生成包含营养计划和护理计划的完整方案。

    参数:
    - async_mode: 是否使用异步模式 (默认false)
      - false: 同步模式，直接返回护理计划结果 (保持原有行为)
      - true: 异步模式，返回task_id，需要轮询 /pet-care/plan/task/{task_id} 查询结果

    工作流程：
    1. 提取和补全宠物基本信息
    2. 并行生成营养计划和护理计划
    3. 验证计划的一致性和安全性
    4. 生成最终结构化输出

    Args:
        request: 包含用户查询和可选宠物信息的请求
        async_mode: 是否使用异步模式

    Returns:
        JSONResponse: 包含营养计划和护理计划的响应，或任务ID（异步模式）
    """
    logger.info(f"收到宠物护理计划请求: {request.user_query[:50]}..., async_mode={async_mode}")

    try:
        # 检查输入是否为空
        if not request.user_query or not request.user_query.strip():
            logger.warning("用户查询为空")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "用户查询不能为空",
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST
                }
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
                TaskType.PET_CARE_PLAN,
                task_data,
                priority=0
            )
            logger.info(f"宠物护理计划任务已提交: {task_id}")
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": "宠物护理计划任务已提交，请使用task_id查询结果",
                    "data": {
                        "task_id": task_id,
                        "status": "pending"
                    },
                    "code": status.HTTP_202_ACCEPTED
                }
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
            pet_info["neutered"] = "true" if request.pet_neutered else "false"  # 转换为字符串

        logger.debug(f"初始宠物信息: {pet_info}")

        # 创建代理并执行工作流
        agent = PetCareAgent()
        result = await agent.run(
            user_query=request.user_query,
            pet_info=pet_info if pet_info else None
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
                "activity_level": result.pet.activity_level
            },
            "nutrition_plan": {
                "daily_calories": result.nutrition_plan.daily_calories,
                "macro_ratio": result.nutrition_plan.macro_ratio,
                "recommended_foods": result.nutrition_plan.recommended_foods,
                "avoid_foods": result.nutrition_plan.avoid_foods,
                "supplements": result.nutrition_plan.supplements,
                "feeding_schedule": result.nutrition_plan.feeding_schedule
            },
            "care_plan": {
                "grooming": result.care_plan.grooming,
                "medical": result.care_plan.medical,
                "exercise": result.care_plan.exercise,
                "vaccination": result.care_plan.vaccination,
                "environment": result.care_plan.environment
            },
            "validation": {
                "risk_analysis": result.reasoning.risk_analysis,
                "contradictions": result.reasoning.contradictions
            },
            "status": {
                "nutrition_plan_ready": result.flags.nutrition_plan_ready,
                "care_plan_ready": result.flags.care_plan_ready,
                "final_output_ready": result.flags.final_output_ready
            }
        }

        # 检查计划是否全部完成
        nutrition_ready = result.flags.nutrition_plan_ready == "true"
        care_ready = result.flags.care_plan_ready == "true"
        if not nutrition_ready or not care_ready:
            logger.warning("部分计划未完成")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "护理计划部分生成成功，部分计划未完成",
                    "data": response_data,
                    "code": status.HTTP_206_PARTIAL_CONTENT
                }
            )

        logger.info("所有计划生成成功")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "宠物护理计划生成成功",
                "data": response_data,
                "code": status.HTTP_200_OK
            }
        )

    except Exception as e:
        logger.error(f"生成宠物护理计划失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": f"护理计划生成服务暂时不可用: {str(e)}",
                "data": None,
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        )


@router.get("/pet-care/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """
    健康检查接口

    Returns:
        JSONResponse: 服务状态
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "宠物护理计划服务运行正常",
            "code": status.HTTP_200_OK,
            "service": "pet-care-plan",
            "version": "1.0.0"
        }
    )


@router.get("/pet-care/plan/task/{task_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def get_pet_care_plan_task_status(
    task_id: str
) -> JSONResponse:
    """
    查询宠物护理计划任务状态和结果（仅用于异步模式）

    返回:
    - pending: 等待中
    - processing: 处理中，包含进度信息
    - completed: 已完成，包含护理计划结果
    - failed: 失败，包含错误信息
    """
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
                "message": "宠物护理计划生成成功",
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
                "message": result.get("error", "宠物护理计划任务执行失败"),
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
                "message": f"正在处理: {progress.get('stage', '生成护理计划中')}",
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


@router.delete("/pet-care/plan/task/{task_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def cancel_pet_care_plan_task(
    task_id: str
) -> JSONResponse:
    """取消宠物护理计划任务（仅用于异步模式）"""
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
