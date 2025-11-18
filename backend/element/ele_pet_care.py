from typing import Optional

from pydantic import BaseModel, Field


class CreatePetCarePlanRequest(BaseModel):
    """创建宠物护理计划请求"""
    user_query: str = Field(
        ...,
        description="用户查询或需求描述",
        example="我家有一只3岁的金毛犬Lucky，体重30公斤，希望制定营养和护理计划"
    )

    # 可选的宠物初始信息
    pet_name: Optional[str] = Field(None, description="宠物名称", example="Lucky")
    pet_species: Optional[str] = Field(None, description="物种", example="狗")
    pet_breed: Optional[str] = Field(None, description="品种", example="金毛")
    pet_age: Optional[str] = Field(None, description="年龄", example="3岁")
    pet_weight: Optional[float] = Field(
        None, description="体重(kg)", example=30.0)
    pet_sex: Optional[str] = Field(None, description="性别", example="male")
    pet_neutered: Optional[bool] = Field(
        None, description="是否绝育", example=True)


class PetCarePlanResponse(BaseModel):
    """宠物护理计划响应"""
    message: str = Field(..., description="响应消息")
    code: int = Field(..., description="状态码")
    data: Optional[dict] = Field(None, description="护理计划数据")
