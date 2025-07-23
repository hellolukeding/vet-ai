import json

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse

from backend.element.ele_diagnosis import CreateDiagnosisRequest
from config.logger import logger
from core.ai_diagnosis import cus_diagnosis

router = APIRouter()

# /*--------------------------------------- api ------------------------------------------*/
@router.post("/diagnosis", response_model=dict, status_code=status.HTTP_200_OK)
async def create_diagnosis(
    diagnosis_data: CreateDiagnosisRequest
) -> JSONResponse:
    """创建诊断并返回诊断结果。"""
    try:
        result = cus_diagnosis.dialog_diagnosis(diagnosis_data.description)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "诊断成功",
                "data": result,
                "code": status.HTTP_200_OK
            }
        )
    except Exception as e:
        logger.error(f"诊断失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": f"诊断失败: {str(e)}",
                "data": None,
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        )