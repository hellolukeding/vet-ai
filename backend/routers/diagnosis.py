import asyncio

from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from backend.element.ele_diagnosis import CreateDiagnosisRequest
from config.logger import logger
from core.diagnosis_assessment import (
    generate_assessment,
    pending_assessment,
    unavailable_assessment,
)
from core.herb_result import format_herb_result
from core.langgraph.agent_herb import herb_graph
from core.langgraph.state_herb import TCAgentState
from core.tasks import TaskType, get_task_manager

router = APIRouter()

# /*--------------------------------------- api ------------------------------------------*/


@router.post(
    "/vet/herb",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="中医智能诊断（LangGraph 高级版）",
    description="""
基于 LangGraph 工作流的先进中医诊断系统，提供多步推理和增强准确性。

### 🌿 功能特性

- **文献搜索**：自动搜索中医古籍和现代中医文献（6条）
- **多步推理**：通过状态机实现复杂中医辨证流程（5节点）
- **辨证论治**：四诊合参、脏腑辨证、气血津液分析
- **方剂推荐**：基础方、加减方、急救方（15个方剂）
- **动态护理**：根据证型动态生成护理建议
- **工作流管理**：支持诊断过程的可视化和管理
- **状态追踪**：实时追踪诊断过程的每个步骤

### 🔄 工作流节点

1. **HerbLiteratureSearch**：搜索中医文献（6条）
2. **HerbDiagnosis**：中医辨证论治（6步 CoT 推理）
3. **HerbPharmacist**：方剂推荐（经典方剂）
4. **HerbNursing**：动态护理建议（根据证型生成）
5. **HerbReport**：生成最终报告

### 🎯 适用场景

- 中医辨证论治
- 草本治疗方案
- 需要多系统分析的综合诊断
- 需要详细推理过程的诊断

### 📋 返回内容

- **zhengming**：证型判断（如脾胃虚弱、寒湿困脾等）
- **description**：证型描述和辨证依据
- **p**：证型概率
- **therapy**：治疗原则
- **base**：基础护理建议（动态生成，根据证型定制）
- **continue**：继续观察建议（动态生成）
- **suggest**：建议就医指征（动态生成）
- **base_prescription**：基础方剂
- **base_prescription_usage**：基础方剂用法
- **continue_prescription**：加减方剂
- **continue_prescription_usage**：加减方剂用法
- **suggest_prescription**：急救方剂
- **suggest_prescription_usage**：急救方剂用法
- **assessment.emergency**：紧急情况识别
- **assessment.recommended_tests**：建议检查项目
- **assessment.temporary_care**：就医前临时处置建议

### 💡 动态护理示例

不同证型的护理建议会动态生成：

**脾胃虚弱夹湿**：
- base: "饮食调理：给予易消化食物，如稀粥、肉泥，少量多餐。避免生冷、油腻。"
- continue: "观察食欲变化：每日记录进食量和精神状态。"

**寒湿困脾**：
- base: "饮食调理：温热饮食，加生姜、胡椒等温热调料。避免生冷寒凉。"
- continue: "观察体温变化：注意是否回暖。"

### 🔄 模式说明

- **同步模式** (`async_mode=false`)：直接返回诊断结果
- **异步模式** (`async_mode=true`)：返回task_id，需轮询查询结果

### ⚡ 性能

- 同步模式：通常 3-5 分钟（包含文献搜索和多步推理）
- 适合：复杂中医辨证和草本治疗
    """.strip(),
    responses={
        200: {
            "description": "中医诊断成功",
            "content": {
                "application/json": {
                    "example": {
                        "message": "中医诊断成功",
                        "disclaimer": "⚠️ 重要声明：本系统提供AI辅助中医诊断建议，仅供参考。中药方剂需由专业中兽医根据宠物具体情况调整。急重症请立即中西医结合就医。",
                        "data": [
                            {
                                "zhengming": "脾胃虚弱夹湿",
                                "description": "基于食欲不振、精神萎靡、大便稀溏等症状，表现为脾失健运、运化失职，湿邪内生。脾胃为后天之本，气血生化之源，脾虚则运化无力，水湿不化，故见食欲不振、大便稀溏；气血生化乏源，则精神萎靡。此证型在宠物消化系统疾病中较为常见。",
                                "p": 0.85,
                                "therapy": "健脾益气，燥湿和胃",
                                "base": "饮食调理：给予易消化食物，如稀粥、肉泥，少量多餐。避免生冷、油腻、难消化食物。环境管理：保持温暖干燥，避免潮湿和直吹空调。适当运动：轻度活动促进气血运行，但避免过度劳累。",
                                "continue": "观察食欲变化：每日记录进食量和精神状态。观察大便性状：注意大便次数、性状是否改善。监测体温：每日测量体温。观察精神状态：注意活动量和反应能力的变化。",
                                "suggest": "立即就医：持续呕吐超过24小时或呕吐物带血。高热不退（>39.5°C）。精神极度萎靡、昏迷。完全拒食超过48小时。大便带血或呈黑色柏油状。",
                                "base_prescription": "参苓白术散加减",
                                "base_prescription_usage": "水煎服，每日1剂，分早晚两次服用。处方：人参10g、白术15g、茯苓15g、山药15g、莲子肉10g、白扁豆10g、薏苡仁20g、砂仁5g（后下）、桔梗10g、甘草5g。可根据体重调整剂量。",
                                "continue_prescription": "香砂六君子汤",
                                "continue_prescription_usage": "水煎服，每日1剂，分早晚两次服用。处方：木香10g、砂仁5g（后下）、陈皮10g、半夏10g、人参10g、白术15g、茯苓15g、甘草5g。适用于脾胃虚弱兼有气滞者。",
                                "suggest_prescription": "理中丸（急救用）",
                                "suggest_prescription_usage": "急救时可选用，但建议立即就医。处方：人参15g、白术20g、干姜10g、甘草10g。适用于脾胃虚寒较重，出现四肢厥冷、脉微欲绝等危重症状。",
                            },
                            {
                                "zhengming": "寒湿困脾",
                                "description": "寒湿之邪困阻中焦，脾胃升降失常。寒主收引，湿性黏滞，寒湿困脾则脾胃运化功能严重受阻。临床以腹痛、腹泻、畏寒为主要表现，多由外感寒湿、内伤生冷所致。",
                                "p": 0.75,
                                "therapy": "温中散寒，燥湿健脾",
                                "base": "饮食调理：温热饮食，可加生姜、胡椒等温热调料。避免生冷寒凉食物。环境管理：特别注意保暖，可使用热水袋或电热毯。避免受凉和潮湿环境。腹部护理：可用温热毛巾热敷腹部。",
                                "continue": "观察体温变化：注意体温是否回暖。观察腹痛情况：注意腹痛部位、性质和程度变化。观察大便性状：是否转为稀便或水样，有无脓血。观察精神状态：有无四肢冰冷、耳鼻发凉。",
                                "suggest": "立即就医：体温持续低于37°C或逐渐下降。四肢冰冷、耳鼻发凉。精神萎靡加重、反应迟钝。腹痛剧烈，呈板状腹。出现休克症状（心率快、血压低）。",
                                "base_prescription": "胃苓汤加减",
                                "base_prescription_usage": "水煎服，每日1剂，分早晚两次服用。处方：苍术15g、厚朴10g、陈皮10g、甘草5g、茯苓20g、猪苓15g、白术15g、泽泻15g、桂枝10g、生姜3片、大枣3枚。温阳化气，健脾利湿。",
                                "continue_prescription": "藿香正气散",
                                "continue_prescription_usage": "水煎服，每日1剂，分早晚两次服用。处方：大腹皮10g、白芷10g、紫苏10g、茯苓15g、半夏曲10g、白术15g、陈皮10g、厚朴10g、藿香15g、甘草5g。适用于外感风寒、内伤湿滞者。",
                                "suggest_prescription": "附子理中丸（急救用）",
                                "suggest_prescription_usage": "急救时可选用，但必须立即就医。处方：制附子10g（先煎30分钟）、人参15g、白术20g、干姜10g、甘草10g。适用于脾肾阳虚，寒湿内阻较重，出现四肢厥逆、下利清谷等危重症状。注意：附子有毒，必须先煎30分钟以上。",
                            },
                        ],
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
                        "disclaimer": "⚠️ 本系统仅提供辅助诊断建议，不能替代专业中兽医的诊断和治疗。紧急情况请立即就医。",
                        "data": None,
                        "code": 400,
                    }
                }
            },
        },
    },
    tags=["中医诊断"],
)
async def create_herb_diagnosis(
    diagnosis_data: CreateDiagnosisRequest,
    async_mode: bool = Query(False, description="是否使用异步模式"),
) -> JSONResponse:
    logger.info(
        f"开始处理中医诊断请求: {diagnosis_data.description}, async_mode={async_mode}"
    )

    assessment = unavailable_assessment()
    try:
        # 检查输入是否为空
        if not diagnosis_data.description or not diagnosis_data.description.strip():
            logger.warning("诊断描述为空")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "诊断描述不能为空",
                    "disclaimer": "⚠️ 本系统仅提供辅助诊断建议，不能替代专业中兽医的诊断和治疗。紧急情况请立即就医。",
                    "data": None,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "assessment": unavailable_assessment(),
                },
            )

        # 异步模式：提交任务并返回task_id
        if async_mode:
            task_manager = get_task_manager()
            task_id = task_manager.submit_task(
                TaskType.HERB_DIAGNOSIS,
                {"symptoms": diagnosis_data.description},
                priority=0,
            )
            logger.info(f"中医诊断任务已提交: {task_id}")
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": "中医诊断任务已提交，请使用task_id查询结果",
                    "data": {"task_id": task_id, "status": "pending"},
                    "code": status.HTTP_202_ACCEPTED,
                    "assessment": pending_assessment(),
                },
            )

        # 同步模式：使用 LangGraph 工作流执行诊断
        state = TCAgentState(description=diagnosis_data.description)

        # 附加评估与原诊断工作流互不依赖，并行可降低同步接口总时延。
        assessment_task = asyncio.create_task(
            generate_assessment(diagnosis_data.description)
        )
        try:
            final_state, assessment = await asyncio.gather(
                herb_graph.ainvoke(state), assessment_task
            )
        except BaseException:
            if not assessment_task.done():
                assessment_task.cancel()
            await asyncio.gather(assessment_task, return_exceptions=True)
            raise

        formatted_result = format_herb_result(final_state)
        logger.info(f"成功格式化 {len(formatted_result)} 个证型结果")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "中医诊断成功",
                "disclaimer": "⚠️ 重要声明：本系统提供AI辅助中医诊断建议，仅供参考。中药方剂需由专业中兽医根据宠物具体情况调整。急重症请立即中西医结合就医。",
                "data": formatted_result,
                "code": status.HTTP_200_OK,
                "assessment": assessment,
            },
        )
    except Exception as e:
        error_msg = repr(e)
        logger.error("中医诊断失败: {}", error_msg, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "中医诊断服务暂时不可用，请稍后重试",
                "disclaimer": "⚠️ 本系统仅提供辅助诊断建议，不能替代专业中兽医。如宠物症状持续或加重，请立即就医。",
                "data": [],
                "code": status.HTTP_200_OK,
                "assessment": assessment,
            },
        )


@router.get(
    "/vet/herb/task/{task_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="查询中医诊断任务状态",
    description="""
查询异步中医诊断任务的执行状态和结果。

### 🔄 任务状态

- **pending**：任务排队中
- **processing**：任务处理中（包含工作流进度）
- **completed**：任务完成，包含诊断结果
- **failed**：任务失败
    """.strip(),
    tags=["中医诊断"],
)
async def get_herb_diagnosis_task_status(task_id: str) -> JSONResponse:
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
                "message": "中医诊断成功",
                "data": result.get("diagnoses", []),
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
                "message": result.get("error", "中医诊断任务执行失败"),
                "data": [],
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
                "message": f"正在处理: {progress.get('stage', '中医诊断中')}",
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
    "/vet/herb/task/{task_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="取消中医诊断任务",
    description="取消正在执行或排队中的中医诊断任务",
    tags=["中医诊断"],
)
async def cancel_herb_diagnosis_task(task_id: str) -> JSONResponse:
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
