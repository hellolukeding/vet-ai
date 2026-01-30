import json
import os
import re
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
    # config via settings with sane defaults
    model_name = settings.MODEL_NAME or "deepseek-ai/DeepSeek-V3"
    base_url = settings.BASE_URL or "https://api-inference.modelscope.cn/v1"
    api_key = settings.API_KEY or ""
    temperature = 0.2
    tools = [
        fetch_webpage_tool,
        web_search_tool
    ]
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # retrieve diagnosis list from state (could be list of pydantic models or dicts)
    diagnosis = getattr(state, "diagnosis", None) or state.get(
        "diagnosis", None)
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
                diag.get("symptom") if isinstance(diag, dict) else str(diag))
            if not name:
                continue

            # run web search for medication guidance
            query = f"宠物 {name} 常用治疗药物及剂量"
            # tools in core.langgraph.tools are synchronous and return JSON strings
            try:
                results_raw = web_search_tool(query)
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
                    content = content_raw if isinstance(content_raw, str) else str(content_raw)
                except Exception:
                    content = ""

                top_results.append({"id": rid, "title": title, "link": link, "snippet": snippet, "content": content})

            search_context.append({"diagnosis": name, "results": top_results})
    except Exception as e:
        logger.error(f"药物检索过程发生错误: {e}", exc_info=True)

    # Prompt the LLM to synthesize medication suggestions using the gathered evidence
    system_instructions = f"""
    当前时间：{current_time}
    你是一位临床兽医药师（中文输出），熟悉小动物常用处方和推荐剂量。
    任务：根据给定的诊断和检索到的网页标题/摘要/页面内容，生成药物建议列表，严格返回 JSON，格式为：
    {{"medications": [{{"symptom": str, "drug_name": str, "dosage": str, "frequency": str}}]}}

    要求：
      - `symptom` 为诊断名称（中文），与输入诊断对应；
      - `drug_name` 写常用药品通用名（中文或英文药名）；
      - `dosage` 给出常用剂量表达（如 "10 mg/kg PO q12h" 或中文 "每千克体重10mg，口服，每12小时一次"）；
      - `frequency` 可填写给药频率简写或说明（如 "q12h"、"每日一次"）；
      - 对每个诊断最多返回3条药物建议；整体不要超过15条；
      - 严格只输出 JSON，不要任何额外文本；不要包含来源链接的完整页面内容，只可在内部用于判断。
      - 不要使用任何Markdown代码块格式（如```json）包装结果。
    """

    # build human-readable context
    context_lines = [f"诊断列表:"]
    for d in diagnosis:
        name = getattr(d, "symptom", None) or (
            d.get("symptom") if isinstance(d, dict) else str(d))
        prob = getattr(d, "probability", None) or (
            d.get("probability") if isinstance(d, dict) else None)
        if prob is not None:
            context_lines.append(f"- {name} (可能性: {prob})")
        else:
            context_lines.append(f"- {name}")

    context_lines.append("\n检索到的证据（每个诊断最多列出3条标题与摘要）:")
    for entry in search_context:
        context_lines.append(f"诊断: {entry['diagnosis']}")
        for r in entry['results']:
            context_lines.append(f"  标题: {r.get('title', '')}")
            if r.get('snippet'):
                context_lines.append(f"  摘要: {r.get('snippet')}")

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instructions),
        HumanMessage(content="\n".join(context_lines))
    ])

    # 尝试使用结构化输出
    try:
        logger.info("尝试使用结构化输出生成药物建议")
        structured_llm = llm.with_structured_output(
            PharmacistSchema, method="json_schema")
        messages = prompt.format_messages()
        response = await structured_llm.ainvoke(messages)
        logger.info(f"结构化输出成功: {response}")
    except Exception as e:
        logger.warning(f"结构化输出调用失败: {e}，尝试使用普通 LLM + JSON 解析")
        # fallback to regular LLM call
        try:
            messages = prompt.format_messages()
            raw_response = await llm.ainvoke(messages)
            logger.info(f"LLM 原始响应: {raw_response.content[:500]}...")  # 记录前500字符

            # 尝试从原始响应中提取JSON
            content = extract_json_from_markdown(raw_response.content)
            logger.debug(f"提取的 JSON 内容: {content}")
            response = json.loads(content)
            logger.info(f"JSON 解析成功: {list(response.keys()) if isinstance(response, dict) else type(response)}")
        except Exception as e2:
            logger.error(f"药剂师节点调用完全失败: {e2}")
            logger.error(f"LLM 原始内容: {raw_response.content if 'raw_response' in locals() else 'N/A'}")

            # 返回默认药物建议
            logger.info("返回默认药物建议")
            return {"medications": [
                MedicationItem(
                    symptom="消化不良/胃肠炎",
                    drug_name="马罗皮剂（Maropitant）",
                    dosage="1 mg/kg，皮下注射或口服，每24小时一次",
                    frequency="每日一次"
                ),
                MedicationItem(
                    symptom="消化不良/胃肠炎",
                    drug_name="奥美拉唑（Omeprazole）",
                    dosage="0.5-1 mg/kg，口服，每24小时一次",
                    frequency="每日一次"
                ),
                MedicationItem(
                    symptom="感染",
                    drug_name="阿莫西林克拉维酸钾",
                    dosage="12.5-25 mg/kg，口服，每12小时一次",
                    frequency="每日两次"
                ),
                MedicationItem(
                    symptom="寄生虫感染",
                    drug_name="芬苯达唑（Fenbendazole）",
                    dosage="50 mg/kg，口服，每日一次，连续3-5天",
                    frequency="每日一次"
                ),
                MedicationItem(
                    symptom="呕吐",
                    drug_name="甲氧氯普胺（Metoclopramide）",
                    dosage="0.2-0.5 mg/kg，口服或皮下注射，每8小时一次",
                    frequency="每日三次"
                )
            ]}

    # Normalize output
    try:
        # Convert pydantic structured output to dict if needed
        if hasattr(response, "model_dump"):
            response = response.model_dump()
            logger.debug(f"转换为字典: {list(response.keys()) if isinstance(response, dict) else type(response)}")

        meds = response.get("medications") if isinstance(response, dict) else None
        if not isinstance(meds, list):
            logger.warning(f"medications 字段不是列表: {type(meds)}, response={response}")
            meds = []

        normalized: List[MedicationItem] = []
        for item in meds:
            symptom = item.get("symptom", "")
            drug_name = item.get("drug_name", "")
            dosage = item.get("dosage", "")
            frequency = item.get("frequency", "")
            normalized.append(MedicationItem(
                symptom=symptom, drug_name=drug_name, dosage=dosage, frequency=frequency))

        logger.info(f"成功规范化 {len(normalized)} 个药物建议")
        return {"medications": normalized}
    except Exception as e:
        logger.error(f"药剂师结果解析失败: {e}", exc_info=True)

        # 返回默认药物建议
        logger.info("返回默认药物建议（fallback from parsing error）")
        return {"medications": [
            MedicationItem(
                symptom="消化不良/胃肠炎",
                drug_name="马罗皮剂（Maropitant）",
                dosage="1 mg/kg，皮下注射或口服，每24小时一次",
                frequency="每日一次"
            ),
            MedicationItem(
                symptom="消化不良/胃肠炎",
                drug_name="奥美拉唑（Omeprazole）",
                dosage="0.5-1 mg/kg，口服，每24小时一次",
                frequency="每日一次"
            ),
            MedicationItem(
                symptom="感染",
                drug_name="阿莫西林克拉维酸钾",
                dosage="12.5-25 mg/kg，口服，每12小时一次",
                frequency="每日两次"
            ),
            MedicationItem(
                symptom="寄生虫感染",
                drug_name="芬苯达唑（Fenbendazole）",
                dosage="50 mg/kg，口服，每日一次，连续3-5天",
                frequency="每日一次"
            ),
            MedicationItem(
                symptom="呕吐",
                drug_name="甲氧氯普胺（Metoclopramide）",
                dosage="0.2-0.5 mg/kg，口服或皮下注射，每8小时一次",
                frequency="每日三次"
            )
        ]}