import asyncio

from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config.logger import logger
from core.diagnosis_assessment import (
    generate_assessment,
    pending_assessment,
    unavailable_assessment,
)
from core.langgraph.agent import graph
from core.langgraph.state import VetAgentState
from core.tasks import TaskType, get_task_manager

router = APIRouter()

# 请求体


class DiagnosisRequest(BaseModel):
    description: str


# @app.post("/vet/diagnose")
@router.post(
    "/vet/diagnose",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="西医智能诊断（LangGraph 高级版）",
    description="""
基于 LangGraph 工作流的先进智能诊断系统，提供多步推理和增强准确性。

### 🧠 功能特性

- **文献搜索**：自动搜索医学文献支持诊断
- **多步推理**：通过状态机实现复杂诊断流程（6节点）
- **诊断审查**：双重质量保证机制
- **安全检查**：每个药物包含安全警告
- **工作流管理**：支持诊断过程的可视化和管理
- **状态追踪**：实时追踪诊断过程的每个步骤

### 🔄 工作流节点

1. **LiteratureSearch**：搜索医学文献（6-10条）
2. **Diagnosis**：CoT 推理诊断（5步显式推理）
3. **DiagnosisReview**：诊断质量审查
4. **Pharmacist**：用药建议（包含给药途径）
5. **SafetyCheck**：安全检查（每个药物独立警告）
6. **Report**：生成最终报告

### 🎯 适用场景

- 复杂疑难病例
- 需要多系统分析的综合诊断
- 需要详细推理过程的诊断
- 需要用药安全评估的场景

### 📋 返回内容

- **description**：症状描述
- **diagnosis**：诊断结果列表（包含疾病名称、依据、概率）
- **medications**：推荐药物列表（每个药物包含安全警告）
- **assessment.emergency**：紧急情况识别
- **assessment.recommended_tests**：建议检查项目
- **assessment.temporary_care**：就医前临时处置建议

### ⚠️ 安全警告

每个药物都包含独立的 `safety_warning` 字段，例如：
- `"⚠️ 氨基糖苷类有肾毒性风险，建议监测肾功能"`
- `"⚠️ 地高辛治疗指数窄，需监测血药浓度"`
- `"✅ 剂量在安全范围内，无明显禁忌"`

### 🔄 模式说明

- **同步模式** (`async_mode=false`)：直接返回诊断结果
- **异步模式** (`async_mode=true`)：返回task_id，需轮询查询结果

### ⚡ 性能

- 同步模式：通常 3-6 分钟（包含文献搜索和多步推理）
- 异步模式：适合复杂诊断任务
    """.strip(),
    responses={
        200: {
            "description": "智能诊断成功",
            "content": {
                "application/json": {
                    "example": {
                        "message": "智能诊断成功",
                        "disclaimer": "⚠️ 重要声明：本系统提供AI辅助诊断建议，仅供参考，不能替代专业兽医的诊断和治疗。所有用药方案必须由执业兽医确认。紧急情况请立即就医。",
                        "data": {
                            "description": "2岁哈士奇，体温30°C，心率40次/分，呕吐不进食",
                            "diagnosis": [
                                {
                                    "symptom": "肾上腺皮质功能减退危象",
                                    "reason": "常见于年轻成年犬，表现为低体温、心动过缓、呕吐不进食等肾上腺皮质功能不全症状。严重低体温（30°C）和心动过缓（40次/分）提示可能存在肾上腺危象。",
                                    "probability": 0.3,
                                },
                                {
                                    "symptom": "阿片类药物或镇静剂中毒",
                                    "reason": "可导致严重中枢神经系统抑制，表现为低体温、心动过缓、胃肠道症状。如有药物接触史可能性更高。",
                                    "probability": 0.25,
                                },
                                {
                                    "symptom": "胃肠梗阻伴休克",
                                    "reason": "呕吐不进食可能导致梗阻，严重梗阻可引起休克，表现为低体温和心动过缓。",
                                    "probability": 0.2,
                                },
                            ],
                            "medications": [
                                {
                                    "symptom": "肾上腺皮质功能减退危象",
                                    "drug_name": "氢化可的松琥珀酸钠",
                                    "dosage": "2-4 mg/kg IV (初始推注)",
                                    "frequency": "q6-8h",
                                    "safety_warning": "✅ 糖皮质激素，剂量在安全范围内。建议监测血压和血糖",
                                },
                                {
                                    "symptom": "胃肠梗阻伴休克",
                                    "drug_name": "恩诺沙星",
                                    "dosage": "5 mg/kg IV",
                                    "frequency": "q24h",
                                    "safety_warning": "⚠️ 对幼年动物（<8个月）有软骨毒性风险，建议慎用或选择替代抗生素",
                                },
                                {
                                    "symptom": "胃肠梗阻伴休克",
                                    "drug_name": "0.9% 氯化钠注射液",
                                    "dosage": "10-20 mL/kg IV",
                                    "frequency": "持续输注",
                                    "safety_warning": "⚠️ 快速输液可能存在液体过载风险，建议监测呼吸频率和肺部听诊",
                                },
                                {
                                    "symptom": "严重环境性低体温",
                                    "drug_name": "阿托品",
                                    "dosage": "0.02-0.04 mg/kg IV",
                                    "frequency": "prn",
                                    "safety_warning": "⚠️ 在低体温情况下效果可能降低，建议优先纠正体温后使用",
                                },
                            ],
                        },
                        "code": 200,
                    }
                }
            },
        },
        400: {
            "description": "请求参数错误（症状描述为空）",
            "content": {
                "application/json": {
                    "example": {
                        "message": "诊断描述不能为空",
                        "disclaimer": "⚠️ 本系统仅提供辅助诊断建议，不能替代专业兽医的诊断和治疗。紧急情况请立即就医。",
                        "data": None,
                        "code": 400,
                    }
                }
            },
        },
    },
    tags=["西医诊断"],
)
async def diagnose(
    request: DiagnosisRequest,
    async_mode: bool = Query(False, description="是否使用异步模式"),
) -> JSONResponse:
    logger.info(
        f"开始处理LangGraph智能诊断请求: {request.description}, async_mode={async_mode}"
    )

    assessment = unavailable_assessment()
    try:
        # 检查输入是否为空
        if not request.description or not request.description.strip():
            logger.warning("诊断描述为空")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "诊断描述不能为空",
                    "disclaimer": "⚠️ 本系统仅提供辅助诊断建议，不能替代专业兽医的诊断和治疗。紧急情况请立即就医。",
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "assessment": unavailable_assessment(),
                },
            )

        # 异步模式：提交任务并返回task_id
        if async_mode:
            task_manager = get_task_manager()
            task_id = task_manager.submit_task(
                TaskType.GRAPH_DIAGNOSIS, {"query": request.description}, priority=0
            )
            logger.info(f"LangGraph智能诊断任务已提交: {task_id}")
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": "智能诊断任务已提交，请使用task_id查询结果",
                    "data": {"task_id": task_id, "status": "pending"},
                    "code": status.HTTP_202_ACCEPTED,
                    "assessment": pending_assessment(),
                },
            )

        # 同步模式：直接执行并返回结果 (保持原有行为)
        state = VetAgentState(description=request.description)

        # 附加评估与原诊断工作流互不依赖，并行可降低同步接口总时延。
        assessment_task = asyncio.create_task(generate_assessment(request.description))
        try:
            final_state, assessment = await asyncio.gather(
                graph.ainvoke(state), assessment_task
            )
        except BaseException:
            if not assessment_task.done():
                assessment_task.cancel()
            await asyncio.gather(assessment_task, return_exceptions=True)
            raise

        # 返回最终结果
        # 处理graph.ainvoke可能返回字典而不是对象的情况
        description = (
            final_state.get("description")
            if isinstance(final_state, dict)
            else getattr(final_state, "description", "")
        )
        diagnosis = (
            final_state.get("diagnosis")
            if isinstance(final_state, dict)
            else getattr(final_state, "diagnosis", [])
        )
        medications = (
            final_state.get("medications")
            if isinstance(final_state, dict)
            else getattr(final_state, "medications", [])
        )

        logger.info(
            f"LangGraph智能诊断完成，返回 {len(diagnosis)} 个诊断结果，{len(medications)} 个用药建议"
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "智能诊断成功",
                "disclaimer": "⚠️ 重要声明：本系统提供AI辅助诊断建议，仅供参考，不能替代专业兽医的诊断和治疗。所有用药方案必须由执业兽医确认。紧急情况请立即就医。",
                "data": {
                    "description": description,
                    "diagnosis": [
                        d.model_dump() if hasattr(d, "model_dump") else d
                        for d in diagnosis
                    ],
                    "medications": [
                        m.model_dump() if hasattr(m, "model_dump") else m
                        for m in medications
                    ],
                },
                "code": status.HTTP_200_OK,
                "assessment": assessment,
            },
        )
    except Exception as e:
        error_msg = repr(e)
        logger.error("LangGraph智能诊断失败: {}", error_msg, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "智能诊断服务暂时不可用，请稍后重试或咨询专业兽医",
                "disclaimer": "⚠️ 本系统仅提供辅助诊断建议，不能替代专业兽医。如宠物症状持续或加重，请立即就医。",
                "data": None,
                "code": status.HTTP_200_OK,
                "assessment": assessment,
            },
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
    tags=["西医诊断"],
)
async def get_graph_diagnosis_task_status(task_id: str) -> JSONResponse:
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
    assessment = task_manager.get_task_assessment(task_id)
    if assessment is None:
        assessment = (
            pending_assessment()
            if task_status in ("pending", "processing")
            else unavailable_assessment()
        )

    # 任务完成
    if task_status == "completed":
        result = task_manager.get_task_result(task_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "智能诊断成功",
                "data": result,
                "code": status.HTTP_200_OK,
                "assessment": assessment,
            },
        )

    # 任务失败
    elif task_status == "failed":
        result = task_manager.get_task_result(task_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": result.get("error", "智能诊断任务执行失败"),
                "data": None,
                "code": status.HTTP_200_OK,
                "assessment": assessment,
            },
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
                    "progress": progress,
                },
                "code": status.HTTP_200_OK,
                "assessment": assessment,
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
                "assessment": assessment,
            },
        )


@router.delete(
    "/vet/diagnose/task/{task_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="取消LangGraph智能诊断任务",
    description="取消正在执行或排队中的LangGraph智能诊断任务",
    tags=["西医诊断"],
)
async def cancel_graph_diagnosis_task(task_id: str) -> JSONResponse:
    task_manager = get_task_manager()
    success = task_manager.cancel_task(task_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": (
                "任务已取消" if success else "任务无法取消（可能已完成或不存在）"
            ),
            "data": {"task_id": task_id, "cancelled": success},
            "code": status.HTTP_200_OK,
        },
    )
