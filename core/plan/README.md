# 宠物护理计划代理 (PetCareAgent)

基于 LangGraph 的宠物护理计划自动生成系统，能够为宠物生成结构化的营养计划和护理计划。

## 功能特性

### 核心功能

- 🐾 **宠物信息提取**: 自动从用户查询中提取宠物基本信息
- 🍖 **营养计划生成**: 基于宠物特征生成个性化营养方案
- 💊 **护理计划生成**: 生成全面的日常护理建议
- ✅ **智能验证**: 检测营养和护理计划之间的冲突
- 📊 **结构化输出**: 生成易于使用的 JSON 格式结果

### 工作流节点

1. **PetInfoNode** - 宠物信息提取节点

   - 提取宠物名称、物种、品种、年龄、体重等基本信息
   - 识别健康状况和过敏源
   - 判断信息完整性

2. **NutritionNode** - 营养计划生成节点

   - 计算每日卡路里需求
   - 制定宏量营养素比例（蛋白质/脂肪/碳水）
   - 推荐适合的食物和补充剂
   - 提供喂养时间表

3. **CareNode** - 护理计划生成节点

   - 美容护理建议（洗澡、梳毛、剪指甲等）
   - 医疗护理建议（体检、驱虫、牙齿护理等）
   - 运动建议（散步、游戏、训练等）
   - 疫苗接种计划
   - 环境管理建议

4. **ValidatorNode** - 验证节点

   - 检查营养与健康状况是否匹配
   - 验证食物推荐与过敏源是否冲突
   - 评估运动与营养的平衡性
   - 识别潜在风险

5. **FinalOutputNode** - 最终输出节点
   - 整合所有信息
   - 生成执行摘要
   - 标记完成状态

## 数据结构

### State (状态类)

```python
class State(BaseModel):
    user_query: str                      # 用户查询
    pet: PetInfo                         # 宠物信息
    nutrition_plan: NutritionPlan        # 营养计划
    care_plan: CarePlan                  # 护理计划
    reasoning: IntermediateReasoning     # 推理过程
    flags: WorkflowFlags                 # 工作流标志
    messages: List[Dict[str, Any]]       # 消息存储
```

### PetInfo (宠物信息)

```python
class PetInfo(BaseModel):
    name: str                    # 宠物名称
    species: str                 # 物种 (dog/cat/rabbit等)
    breed: str                   # 品种
    age: str                     # 年龄
    weight: float                # 体重 (kg)
    sex: str                     # 性别
    neutered: bool               # 是否绝育
    health_conditions: List[str] # 健康状况
    allergies: List[str]         # 过敏源
    feeding_history: str         # 喂养历史
    activity_level: str          # 活动水平 (low/medium/high)
```

### NutritionPlan (营养计划)

```python
class NutritionPlan(BaseModel):
    daily_calories: float              # 每日卡路里 (kcal)
    macro_ratio: Dict[str, float]      # 营养比例 {protein, fat, carbs}
    recommended_foods: List[str]       # 推荐食物
    avoid_foods: List[str]             # 避免食物
    supplements: List[str]             # 营养补充剂
    feeding_schedule: List[str]        # 喂养时间表
```

### CarePlan (护理计划)

```python
class CarePlan(BaseModel):
    grooming: List[str]      # 美容护理
    medical: List[str]       # 医疗护理
    exercise: List[str]      # 运动建议
    vaccination: List[str]   # 疫苗接种
    environment: List[str]   # 环境管理
```

## 使用方法

### 基本使用

```python
import asyncio
from core.plan.agent import PetCareAgent

async def main():
    # 创建代理实例
    agent = PetCareAgent()

    # 运行代理
    result = await agent.run(
        user_query="帮我为3岁的金毛Lucky制定营养和护理计划",
        pet_info={
            "name": "Lucky",
            "species": "dog",
            "breed": "金毛",
            "age": "3 years",
            "weight": 30.0,
            "activity_level": "high"
        }
    )

    # 访问结果
    print(f"每日卡路里: {result.nutrition_plan.daily_calories} kcal")
    print(f"推荐食物: {result.nutrition_plan.recommended_foods}")
    print(f"运动建议: {result.care_plan.exercise}")

asyncio.run(main())
```

### 处理特殊健康状况

```python
result = await agent.run(
    user_query="为我患有糖尿病的猫咪制定特殊护理计划",
    pet_info={
        "name": "Mimi",
        "species": "cat",
        "age": "10 years",
        "weight": 5.0,
        "health_conditions": ["糖尿病"],
        "allergies": ["鱼类"],
        "activity_level": "low"
    }
)
```

### 保存结果为 JSON

```python
import json

result = await agent.run(...)

# 转换为字典
result_dict = {
    "pet": result.pet.model_dump(),
    "nutrition_plan": result.nutrition_plan.model_dump(),
    "care_plan": result.care_plan.model_dump(),
}

# 保存
with open("pet_care_plan.json", "w", encoding="utf-8") as f:
    json.dump(result_dict, f, ensure_ascii=False, indent=2)
```

## 运行测试

```bash
# 运行测试示例
python test_pet_care_agent.py
```

## 工作流可视化

```python
from core.plan.agent import PetCareAgent

agent = PetCareAgent()
agent.get_graph_image("workflow.png")
```

## 配置要求

在 `backend/settings.py` 中配置以下参数：

```python
MODEL_NAME = "deepseek-ai/DeepSeek-V3"
BASE_URL = "https://api-inference.modelscope.cn/v1"
API_KEY = "your-api-key"
```

## 依赖项

- langgraph >= 0.1.0
- langchain >= 0.1.0
- langchain-openai >= 0.1.0
- pydantic >= 2.0.0

## 架构说明

```
PetCareAgent
├── PetInfoNode (提取宠物信息)
│   └── 输出: pet, flags.need_pet_info_completion
├── NutritionNode (生成营养计划)
│   └── 输出: nutrition_plan, reasoning.nutrition_agent_notes
├── CareNode (生成护理计划)
│   └── 输出: care_plan, reasoning.care_agent_notes
├── ValidatorNode (验证一致性)
│   └── 输出: reasoning.risk_analysis, reasoning.contradictions
└── FinalOutputNode (最终输出)
    └── 输出: flags.final_output_ready
```

## 扩展建议

1. **添加数据库支持**: 保存历史计划和宠物档案
2. **集成外部 API**: 查询宠物食品营养信息、兽医诊所等
3. **添加提醒功能**: 定期喂养、用药、体检提醒
4. **多语言支持**: 支持英文等其他语言
5. **Web 界面**: 开发用户友好的前端界面
6. **PDF 导出**: 生成可打印的护理计划 PDF

## 注意事项

- 本系统生成的建议仅供参考，不能替代专业兽医的诊断和建议
- 对于有严重健康问题的宠物，请务必咨询专业兽医
- 定期更新宠物信息以获得更准确的计划建议

## License

MIT License
