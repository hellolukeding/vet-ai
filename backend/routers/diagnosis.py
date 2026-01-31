from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from backend.element.ele_diagnosis import CreateDiagnosisRequest
from config.logger import logger
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
                },
            )

        # 同步模式：使用 LangGraph 工作流执行诊断
        state = TCAgentState(description=diagnosis_data.description)

        # 运行中医诊断 Graph
        final_state = await herb_graph.ainvoke(state)

        # 返回最终结果
        zhengming = (
            final_state.get("zhengming")
            if isinstance(final_state, dict)
            else getattr(final_state, "zhengming", [])
        )
        prescriptions = (
            final_state.get("prescriptions")
            if isinstance(final_state, dict)
            else getattr(final_state, "prescriptions", [])
        )
        nursing = (
            final_state.get("nursing")
            if isinstance(final_state, dict)
            else getattr(final_state, "nursing", [])
        )

        # 详细调试：检查数据类型
        logger.debug(f"final_state type: {type(final_state)}")
        logger.debug(
            f"zhengming type: {type(zhengming)}, value: {zhengming if not isinstance(zhengming, list) or len(zhengming) < 5 else f'[list with {len(zhengming)} items]'}"
        )
        logger.debug(
            f"prescriptions type: {type(prescriptions)}, count: {len(prescriptions) if isinstance(prescriptions, list) else 'N/A'}"
        )
        logger.debug(
            f"nursing type: {type(nursing)}, count: {len(nursing) if isinstance(nursing, list) else 'N/A'}"
        )

        # 如果 zhengming 是字符串，需要解析它
        if isinstance(zhengming, str):
            logger.warning(f"zhengming 是字符串而非列表: {zhengming}")
            # 尝试从 JSON 解析
            try:
                import json

                zhengming = json.loads(zhengming)
                logger.info(f"成功从 JSON 解析 zhengming: {len(zhengming)} 项")
            except (json.JSONDecodeError, TypeError):
                logger.error("无法解析 zhengming 字符串，设置为空列表")
                zhengming = []

        logger.info(
            f"中医诊断完成，返回 {len(zhengming)} 个证型，{len(prescriptions)} 个方剂，{len(nursing)} 条护理建议"
        )

        # 提取护理建议（按类别分组）
        base_nursing = next(
            (n.content for n in nursing if getattr(n, "category", "") == "base"),
            "饮食清淡易消化，保持环境温暖，适当运动",
        )
        continue_nursing = next(
            (n.content for n in nursing if getattr(n, "category", "") == "continue"),
            "观察症状变化，监测精神状态",
        )
        suggest_nursing = next(
            (n.content for n in nursing if getattr(n, "category", "") == "suggest"),
            "持续呕吐腹泻或高热应立即就医",
        )

        # 格式化返回数据以兼容原有格式
        formatted_result = []
        try:
            for idx, z in enumerate(zhengming):
                logger.debug(f"处理证型 {idx}: type(z)={type(z)}, z={z}")
                z_dict = z.dict() if hasattr(z, "dict") else z
                # 确保 z_dict 是字典
                if not isinstance(z_dict, dict):
                    logger.warning(f"证型 {idx} 不是字典: {type(z_dict)}, 值: {z_dict}")
                    continue
                zhengming_name = z_dict.get("zhengming", "")
                logger.debug(f"处理证型: {zhengming_name}")

                # 查找对应方剂（使用更宽松的匹配）
                related_prescriptions = []
                for p in prescriptions:
                    p_zhengming = getattr(p, "zhengming", "")
                    # 使用包含匹配，因为证型名称可能有细微差异
                    if p_zhengming and (
                        p_zhengming == zhengming_name
                        or zhengming_name in p_zhengming
                        or p_zhengming in zhengming_name
                    ):
                        related_prescriptions.append(p)

                logger.debug(f"找到 {len(related_prescriptions)} 个相关方剂")

                # 安全地转换为字典列表
                p_dict_list = []
                for idx, p in enumerate(related_prescriptions):
                    logger.debug(
                        f"方剂 {idx} type={type(p)}, zhengming={getattr(p, 'zhengming', '')}, prescription_type={getattr(p, 'prescription_type', '')}"
                    )
                    if hasattr(p, "dict"):
                        p_dict = p.dict()
                        logger.debug(f"方剂字典: {p_dict}")
                        # 验证必需字段存在且为字符串类型
                        if isinstance(p_dict, dict):
                            # 确保所有字段都是JSON可序列化类型
                            safe_dict = {}
                            for key, value in p_dict.items():
                                if value is None:
                                    safe_dict[key] = ""
                                elif not isinstance(
                                    value, (str, int, float, bool, list, dict)
                                ):
                                    safe_dict[key] = str(value)
                                else:
                                    safe_dict[key] = value
                            p_dict_list.append(safe_dict)
                        else:
                            logger.warning(f"p.dict() 未返回字典: {type(p_dict)}")
                    elif isinstance(p, dict):
                        p_dict_list.append(p)
                    else:
                        logger.warning(f"跳过无效的方剂对象: {type(p)}, 值: {p}")

                logger.debug(
                    f"p_dict_list 包含 {len(p_dict_list)} 个方剂: {p_dict_list}"
                )

                # 分类方剂（确保是字典类型）
                # 使用更严格的检查确保找到的是dict对象
                base_presc = next(
                    (
                        p
                        for p in p_dict_list
                        if isinstance(p, dict)
                        and p.get("prescription_type") == "基础方"
                    ),
                    {},
                )
                continue_presc = next(
                    (
                        p
                        for p in p_dict_list
                        if isinstance(p, dict)
                        and p.get("prescription_type") == "加减方"
                    ),
                    {},
                )
                suggest_presc = next(
                    (
                        p
                        for p in p_dict_list
                        if isinstance(p, dict)
                        and p.get("prescription_type") == "急救方"
                    ),
                    {},
                )

                # 额外安全检查：确保结果确实是dict
                if not isinstance(base_presc, dict):
                    logger.warning(
                        f"base_presc 不是dict: {type(base_presc)}, 值: {base_presc}"
                    )
                    base_presc = {}
                if not isinstance(continue_presc, dict):
                    logger.warning(
                        f"continue_presc 不是dict: {type(continue_presc)}, 值: {continue_presc}"
                    )
                    continue_presc = {}
                if not isinstance(suggest_presc, dict):
                    logger.warning(
                        f"suggest_presc 不是dict: {type(suggest_presc)}, 值: {suggest_presc}"
                    )
                    suggest_presc = {}

                logger.debug(
                    f"分类后的方剂 - base: {base_presc}, continue: {continue_presc}, suggest: {suggest_presc}"
                )

                formatted_result.append(
                    {
                        "zhengming": zhengming_name,
                        "description": z_dict.get("description", ""),
                        "p": float(z_dict.get("probability", 0.0)),  # 确保是 float 类型
                        "therapy": z_dict.get("therapy", ""),
                        "base": str(base_nursing)
                        if base_nursing
                        else "",  # 确保是字符串
                        "continue": str(continue_nursing) if continue_nursing else "",
                        "suggest": str(suggest_nursing) if suggest_nursing else "",
                        "base_prescription": base_presc.get("prescription_name", "")
                        if isinstance(base_presc, dict)
                        else "",
                        "base_prescription_usage": base_presc.get("usage", "")
                        if isinstance(base_presc, dict)
                        else "",
                        "continue_prescription": continue_presc.get(
                            "prescription_name", ""
                        )
                        if isinstance(continue_presc, dict)
                        else "",
                        "continue_prescription_usage": continue_presc.get("usage", "")
                        if isinstance(continue_presc, dict)
                        else "",
                        "suggest_prescription": suggest_presc.get(
                            "prescription_name", ""
                        )
                        if isinstance(suggest_presc, dict)
                        else "",
                        "suggest_prescription_usage": suggest_presc.get("usage", "")
                        if isinstance(suggest_presc, dict)
                        else "",
                    }
                )
        except Exception as format_error:
            logger.error(f"格式化结果失败: {format_error}", exc_info=True)
            raise

        logger.info(f"成功格式化 {len(formatted_result)} 个证型结果")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "中医诊断成功",
                "disclaimer": "⚠️ 重要声明：本系统提供AI辅助中医诊断建议，仅供参考。中药方剂需由专业中兽医根据宠物具体情况调整。急重症请立即中西医结合就医。",
                "data": formatted_result,
                "code": status.HTTP_200_OK,
            },
        )
    except Exception as e:
        error_msg = repr(e)
        logger.error("中医诊断失败: %s", error_msg, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "中医诊断服务暂时不可用，请稍后重试",
                "disclaimer": "⚠️ 本系统仅提供辅助诊断建议，不能替代专业中兽医。如宠物症状持续或加重，请立即就医。",
                "data": [],
                "code": status.HTTP_200_OK,
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

    # 任务完成
    if task_status == "completed":
        result = task_manager.get_task_result(task_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "中医诊断成功",
                "data": result.get("diagnoses", []),
                "code": status.HTTP_200_OK,
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
            "message": "任务已取消"
            if success
            else "任务无法取消（可能已完成或不存在）",
            "data": {"task_id": task_id, "cancelled": success},
            "code": status.HTTP_200_OK,
        },
    )
