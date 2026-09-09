import asyncio
import json
from datetime import datetime
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config.logger import logger
from core.langgraph.state import MedicationItem, VetAgentState
from core.langgraph.tools import fetch_webpage_tool, web_search_tool
from core.langgraph.tools.web_search import is_trusted_veterinary_source
from core.llm_factory import create_chat_llm, invoke_json_model


class PharmacistSchema(BaseModel):
    """
    药剂师节点的状态 schema。
    包含药品建议列表。
    """

    medications: List[MedicationItem] = Field(
        ..., max_length=5, description="药品建议列表"
    )


async def PharmacistNode(state: VetAgentState) -> Dict[str, List[MedicationItem]]:
    # 在这里实现药剂师节点的逻辑
    temperature = 0.2
    # 使用百度搜索（中文医学内容质量更好）
    use_baidu = True
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # retrieve diagnosis list from state (could be list of pydantic models or dicts)
    diagnosis = getattr(state, "diagnosis", None) or state.get("diagnosis", None)
    description = getattr(state, "description", "") or state.get("description", "")
    if not diagnosis or not isinstance(diagnosis, list):
        return {"medications": []}

    try:
        llm = create_chat_llm(temperature=temperature)
    except Exception as e:
        logger.error(f"药剂师节点LLM初始化失败: {e}")
        logger.warning("药剂师节点LLM配置不可用，不提供默认用药建议以确保安全性")
        return {"medications": []}

    # Build search snippets for context
    async def search_medication(diag) -> dict:
        name = getattr(diag, "symptom", None) or (
            diag.get("symptom") if isinstance(diag, dict) else str(diag)
        )
        if not name:
            return {"diagnosis": "", "results": []}
        try:
            raw = await web_search_tool.ainvoke(
                {
                    "query": f"宠物 {name} 兽医 治疗指南 用药",
                    "num_results": 3,
                    "use_baidu": use_baidu,
                }
            )
            results = json.loads(raw) if isinstance(raw, str) else raw
            usable = [r for r in (results or [])[:3] if is_trusted_veterinary_source(r)]

            async def enrich(result: dict) -> dict:
                content = ""
                try:
                    if result.get("id"):
                        content = str(
                            await fetch_webpage_tool.ainvoke(
                                {"result_id": result["id"]}
                            )
                        )[:2000]
                except Exception as exc:
                    logger.debug("获取药物网页失败: {}", exc)
                return {**result, "content": content}

            return {
                "diagnosis": name,
                "results": list(await asyncio.gather(*(enrich(r) for r in usable))),
            }
        except Exception as exc:
            logger.warning("药物检索失败 [{}]: {}", name, exc)
            return {"diagnosis": name, "results": []}

    search_context = list(
        await asyncio.gather(*(search_medication(d) for d in diagnosis[:3]))
    )

    # Prompt the LLM to synthesize medication suggestions using the gathered evidence
    system_instructions = f"""
    当前时间：{current_time}
    你是一位临床兽医药师（中文输出），熟悉小动物常用处方和推荐剂量。

    ## 任务
    根据诊断结果和检索到的医学证据，生成药物建议列表。严格返回 JSON。

    ## 安全要求（CRITICAL）
    ⚠️ 你是AI辅助系统，所有用药建议必须由执业兽医确认！
    1. **仅推荐标准处方药**：不要推荐未经验证的偏方或人用药
    2. **信息不足时不猜剂量**：未提供物种、体重、年龄、肝肾功能和既往用药时，dosage 写明“需由兽医按体重和检查结果确定”
    3. **禁忌症警示**：对于危险药物必须标注禁忌（如肾衰竭避免使用氨基糖苷类）
    4. **儿童/妊娠安全**：如果相关，说明幼年、妊娠、哺乳期注意事项
    5. **药物相互作用**：如果多药联用，提示潜在相互作用
    6. **避免过度治疗**：症状轻微、短暂，且精神、食欲、饮水、排便正常、无呼吸困难等危险信号时，medications 必须返回空列表，优先观察和复诊

    ## 推理步骤
    1. **诊断分析**：理解每个诊断的病理生理机制
    2. **文献证据**：参考检索到的权威医学资料
    3. **药物选择**：选择一线治疗药物（优先兽药批准、循证医学支持）
    4. **剂量计算**：根据标准兽药手册推荐剂量
    5. **安全性审核**：检查禁忌症、副作用、药物相互作用

    ## 输出格式
    JSON: {{"medications": [{{"symptom": str, "drug_name": str, "dosage": str, "frequency": str}}]}}

    ## 用药示例
    诊断：肾上腺皮质功能减退危象
    期望输出：
    {{
      "medications": [
        {{"symptom": "肾上腺皮质功能减退危象", "drug_name": "氢化可的松琥珀酸钠", "dosage": "2-4 mg/kg IV (初始推注)", "frequency": "q6-8h"}},
        {{"symptom": "肾上腺皮质功能减退危象", "drug_name": "0.9%氯化钠注射液", "dosage": "20-60 ml/kg IV (休克推注)", "frequency": "持续输注"}},
        {{"symptom": "肾上腺皮质功能减退危象", "drug_name": "地塞米松", "dosage": "0.1-0.2 mg/kg IV/IM", "frequency": "q12-24h"}}
      ]
    }}

    ## 要求
      - `symptom` 为诊断名称（中文），与输入诊断对应
      - `drug_name` 写常用药品通用名（中文或英文药名，优先使用通用名）
      - `dosage` 给出常用剂量表达（如 "10 mg/kg PO q12h" 或中文 "每千克体重10mg，口服，每12小时一次"）
      - `frequency` 可填写给药频率简写或说明（如 "q12h"、"每日一次"）
      - 只为有明确适应证的高可能性诊断给出建议；可以返回空列表
      - 对每个诊断最多返回1条药物建议；整体不要超过5条
      - 剂量必须明确给药途径（IV=静脉, IM=肌肉, PO=口服, SC=皮下）
      - 严格只输出 JSON，不要任何额外文本
      - 不要使用任何Markdown代码块格式（如```json）包装结果
    """

    # build human-readable context
    context_lines = [f"原始症状描述: {description}", "诊断列表:"]
    for d in diagnosis:
        name = getattr(d, "symptom", None) or (
            d.get("symptom") if isinstance(d, dict) else str(d)
        )
        prob = getattr(d, "probability", None) or (
            d.get("probability") if isinstance(d, dict) else None
        )
        if prob is not None:
            context_lines.append(f"- {name} (可能性: {prob})")
        else:
            context_lines.append(f"- {name}")

    context_lines.append("\n检索到的证据（每个诊断最多列出3条标题与摘要）:")
    for entry in search_context:
        context_lines.append(f"诊断: {entry['diagnosis']}")
        for r in entry["results"]:
            context_lines.append(f"  标题: {r.get('title', '')}")
            if r.get("snippet"):
                context_lines.append(f"  摘要: {r.get('snippet')}")

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_instructions),
            HumanMessage(content="\n".join(context_lines)),
        ]
    )

    try:
        messages = prompt.format_messages()
        response = (
            await invoke_json_model(llm, messages, PharmacistSchema)
        ).model_dump()
    except Exception as e:
        logger.error(f"药剂师节点调用失败: {e}")
        logger.warning("药物LLM调用失败，不提供默认药物建议以确保安全性")
        return {"medications": []}

    # Normalize output
    try:
        # Convert pydantic structured output to dict if needed
        if hasattr(response, "model_dump"):
            response = response.model_dump()
            logger.debug(
                f"转换为字典: {list(response.keys()) if isinstance(response, dict) else type(response)}"
            )

        meds = response.get("medications") if isinstance(response, dict) else None
        if not isinstance(meds, list):
            logger.warning(
                f"medications 字段不是列表: {type(meds)}, response={response}"
            )
            meds = []

        normalized: List[MedicationItem] = []
        for item in meds:
            symptom = item.get("symptom", "")
            drug_name = item.get("drug_name", "")
            dosage = item.get("dosage", "")
            frequency = item.get("frequency", "")
            normalized.append(
                MedicationItem(
                    symptom=symptom,
                    drug_name=drug_name,
                    dosage=dosage,
                    frequency=frequency,
                )
            )

        logger.info(f"成功规范化 {len(normalized)} 个药物建议")
        return {"medications": normalized}
    except Exception as e:
        logger.error(f"药剂师结果解析失败: {e}", exc_info=True)

        # 返回空列表而非默认药物建议（医学项目必须严谨，不能提供不准确的药物建议）
        logger.warning("药物结果解析失败，返回空列表以确保安全性")
        return {"medications": []}
