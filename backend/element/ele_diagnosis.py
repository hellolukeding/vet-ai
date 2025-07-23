from pydantic import BaseModel, Field


class CreateDiagnosisRequest(BaseModel):
    description: str = Field(..., example="宠物咳嗽，持续时间2周")
