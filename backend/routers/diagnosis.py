import json
from typing import Any, Dict, List, Union

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse

from backend.element.ele_diagnosis import CreateDiagnosisRequest
from config.logger import logger
from core.ai_diagnosis.diagnosis import Diagnosis
from core.ai_diagnosis.herb_diagnosis import HerbDiagnosis
from core.ai_diagnosis.re_diagnosis import ReDiagnosis

router = APIRouter()

# /*--------------------------------------- api ------------------------------------------*/

@router.post("/diagnosis", response_model=dict, status_code=status.HTTP_200_OK)
async def create_diagnosis(
    diagnosis_data: CreateDiagnosisRequest
) -> JSONResponse:
    """创建诊断并返回诊断结果。"""
    logger.info(f"开始处理诊断请求: {diagnosis_data.description}")
    
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
        logger.error(f"诊断失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,  # 改为200状态码，但内容表示错误
            content={
                "message": "诊断服务暂时不可用，请稍后重试",
                "data": [],
                "code": status.HTTP_200_OK
            }
        )
        
        

@router.post("/herb", response_model=dict, status_code=status.HTTP_200_OK)
async def create_diagnosis(
    diagnosis_data: CreateDiagnosisRequest
) -> JSONResponse:
    """创建诊断并返回诊断结果。"""
    logger.info(f"开始处理诊断请求: {diagnosis_data.description}")
    
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
        logger.error(f"诊断失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,  # 改为200状态码，但内容表示错误
            content={
                "message": "诊断服务暂时不可用，请稍后重试",
                "data": [],
                "code": status.HTTP_200_OK
            }
        )