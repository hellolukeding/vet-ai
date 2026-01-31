import json
from datetime import datetime
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from backend.settings import settings
from config.logger import logger
from core.langgraph.state import MedicationItem, VetAgentState
from core.langgraph.tools import fetch_webpage_tool, web_search_tool
from utils.json.extract_json_from_markdown import extract_json_from_markdown


class PharmacistSchema(BaseModel):
    """
    药剂师节点的状态 schema。
    包含药品建议列表。
    """

    medications: List[MedicationItem] = Field(..., description="药品建议列表")


async def PharmacistNode(state: VetAgentState) -> Dict[str, List[MedicationItem]]:
    # 在这里实现药剂师节点的逻辑
    # 获取配置
    model_name = settings.MODEL_NAME or "deepseek-ai/DeepSeek-V3"
    base_url = settings.BASE_URL or "https://api-inference.modelscope.cn/v1"
    api_key = settings.API_KEY or ""
    temperature = 0.2
    # 使用百度搜索（中文医学内容质量更好）
    use_baidu = True
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # retrieve diagnosis list from state (could be list of pydantic models or dicts)
    diagnosis = getattr(state, "diagnosis", None) or state.get("diagnosis", None)
    if not diagnosis or not isinstance(diagnosis, list):
        return {"medications": []}

    llm = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
    )

    # Build search snippets for context
    search_context = []
    try:
        for diag in diagnosis[:5]:
            # diag may be a pydantic model or dict
            name = getattr(diag, "symptom", None) or (
                diag.get("symptom") if isinstance(diag, dict) else str(diag)
            )
            if not name:
                continue

            # run web search for medication guidance
            query = f"宠物 {name} 常用治疗药物及剂量"
            # tools in core.langgraph.tools are synchronous and return JSON strings
            try:
                results_raw = web_search_tool.invoke(
                    {
                        "query": query,
                        "num_results": 3,
                        "use_baidu": use_baidu,  # 使用百度搜索（中文医学内容更好）
                    }
                )
                # web_search_tool may return a JSON string
                if isinstance(results_raw, str):
                    results = json.loads(results_raw)
                else:
                    results = results_raw
            except Exception:
                results = []

            top_results = []
            for r in (results or [])[:3]:
                rid = r.get("id", "")
                title = r.get("title", "")
                link = r.get("link", "")
                snippet = r.get("snippet", "")

                # fetch full content if available -- pass the result id (tool expects id)
                try:
                    content_raw = fetch_webpage_tool(rid)
                    content = (
                        content_raw
                        if isinstance(content_raw, str)
                        else str(content_raw)
                    )
                except Exception:
                    content = ""

                top_results.append(
                    {
                        "id": rid,
                        "title": title,
                        "link": link,
                        "snippet": snippet,
                        "content": content,
                    }
                )

            search_context.append({"diagnosis": name, "results": top_results})
    except Exception as e:
        logger.error(f"药物检索过程发生错误: {e}", exc_info=True)

    # Prompt the LLM to synthesize medication suggestions using the gathered evidence
    system_instructions = f"""
    当前时间：{current_time}
    你是一位临床兽医药师（中文输出），熟悉小动物常用处方和推荐剂量。

    ## 任务
    根据诊断结果和检索到的医学证据，生成药物建议列表。严格返回 JSON。

    ## 安全要求（CRITICAL）
    ⚠️ 你是AI辅助系统，所有用药建议必须由执业兽医确认！
    1. **仅推荐标准处方药**：不要推荐未经验证的偏方或人用药
    2. **剂量必须精确**：基于体重计算，明确单位（mg/kg, mcg/kg等）
    3. **禁忌症警示**：对于危险药物必须标注禁忌（如肾衰竭避免使用氨基糖苷类）
    4. **儿童/妊娠安全**：如果相关，说明幼年、妊娠、哺乳期注意事项
    5. **药物相互作用**：如果多药联用，提示潜在相互作用

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
      - 对每个诊断最多返回3条药物建议；整体不要超过15条
      - 剂量必须明确给药途径（IV=静脉, IM=肌肉, PO=口服, SC=皮下）
      - 严格只输出 JSON，不要任何额外文本
      - 不要使用任何Markdown代码块格式（如```json）包装结果
    """

    # build human-readable context
    context_lines = ["诊断列表:"]
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

    # 尝试使用结构化输出
    try:
        logger.info("尝试使用结构化输出生成药物建议")
        structured_llm = llm.with_structured_output(
            PharmacistSchema, method="json_schema"
        )
        messages = prompt.format_messages()
        response = await structured_llm.ainvoke(messages)
        logger.info(f"结构化输出成功: {response}")
    except Exception as e:
        logger.warning(f"结构化输出调用失败: {e}，尝试使用普通 LLM + JSON 解析")
        # fallback to regular LLM call
        try:
            messages = prompt.format_messages()
            raw_response = await llm.ainvoke(messages)
            logger.info(
                f"LLM 原始响应: {raw_response.content[:500]}..."
            )  # 记录前500字符

            # 尝试从原始响应中提取JSON
            content = extract_json_from_markdown(raw_response.content)
            logger.debug(f"提取的 JSON 内容: {content}")
            response = json.loads(content)
            logger.info(
                f"JSON 解析成功: {list(response.keys()) if isinstance(response, dict) else type(response)}"
            )
        except Exception as e2:
            logger.error(f"药剂师节点调用完全失败: {e2}")
            logger.error(
                f"LLM 原始内容: {raw_response.content if 'raw_response' in locals() else 'N/A'}"
            )

            # 返回空列表而非默认药物建议（医学项目必须严谨）
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
