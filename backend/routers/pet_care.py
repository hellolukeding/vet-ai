"""
宠物护理计划路由模块

提供基于LangGraph的宠物护理计划生成接口，包括营养计划和护理计划。
"""

from typing import Any, Dict

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from backend.element.ele_pet_care import (CreatePetCarePlanRequest,
                                          PetCarePlanResponse)
from config.logger import logger
from core.plan.agent import PetCareAgent

router = APIRouter()


@router.post("/pet-care/plan", response_model=PetCarePlanResponse, status_code=status.HTTP_200_OK)
async def create_pet_care_plan(
    request: CreatePetCarePlanRequest
) -> JSONResponse:
    """
    创建宠物护理计划

    根据用户提供的宠物信息和需求，生成包含营养计划和护理计划的完整方案。

    工作流程：
    1. 提取和补全宠物基本信息
    2. 并行生成营养计划和护理计划
    3. 验证计划的一致性和安全性
    4. 生成最终结构化输出

    Args:
        request: 包含用户查询和可选宠物信息的请求

    Returns:
        JSONResponse: 包含营养计划和护理计划的响应
    """
    logger.info(f"收到宠物护理计划请求: {request.user_query[:50]}...")

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
        if request.pet_weight:
            pet_info["weight"] = request.pet_weight
        if request.pet_sex:
            pet_info["sex"] = request.pet_sex
        if request.pet_neutered is not None:
            pet_info["neutered"] = request.pet_neutered

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
        if not result.flags.nutrition_plan_ready or not result.flags.care_plan_ready:
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
