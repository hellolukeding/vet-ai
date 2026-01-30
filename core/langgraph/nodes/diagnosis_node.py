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
from core.langgraph.state import DiagnosisItem, VetAgentState
from utils.json.extract_json_from_markdown import extract_json_from_markdown


class DiagnosisSchema(BaseModel):
    """Expected structured output from the LLM.

    diagnosis: a list of diagnosis items. Each item must contain:
      - symptom: the name of the suspected disease/diagnosis
      - reason: a short rationale citing the key symptoms/evidence
      - probability: a float between 0 and 1 indicating likelihood
    """

    diagnosis: List[DiagnosisItem] = Field(..., description="诊断列表")


async def DiagnosisNode(state: VetAgentState) -> Dict[str, List[DiagnosisItem]]:
    """Generate diagnostic suggestions from `state.description` and return a VetAgentState-like dict.

    Contract:
      - input: state with `description: str` (one-line pet symptom description)
      - output: dict matching VetAgentState with `diagnosis: list[DiagnosisItem]`
    """

    # config via settings with sane defaults
    model_name = settings.MODEL_NAME or "deepseek-ai/DeepSeek-V3"
    base_url = settings.BASE_URL or "https://api-inference.modelscope.cn/v1"
    api_key = settings.API_KEY or ""
    temperature = 0.6

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    description = getattr(state, "description",
                          "") or state.get("description", "")

    if not description:
        return {"diagnosis": []}

    llm = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
    )

    # Clear, precise system prompt to encourage exact JSON output matching DiagnosisSchema
    system_instructions = f"""
    当前时间：{current_time}
    你是一位资深兽医（中文输出），对小动物临床表现、鉴别诊断和常用处方非常熟悉。
    任务：根据下面的症状描述，列出最少5个最可能的诊断。返回严格的JSON，不要包含额外的文本。JSON schema: {{"diagnosis": [{{"symptom": str, "reason": str, "probability": float}}]}}

    要求：
      - 必须输出至少5个诊断结果，按可能性从高到低排序
      - 每个诊断的 `symptom` 字段写疾病或综合征的简短名称（中文）。
      - `reason` 简洁说明为何该诊断成立，引用症状/体征/病史要点（2-3项）。
      - `probability` 为 0 到 1 的小数，三位小数精度优先，总和不用严格为1，但请确保相对合理。
      - 返回的诊断数量 >= 5，按可能性从高到低排序。
      - 如果症状信息有限，也要尽可能提供5个可能的鉴别诊断
      - 不要返回诊断以外的段落说明或解释文本，严格只输出 JSON。
      - 不要使用任何Markdown代码块格式（如```json）包装结果。
    """

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instructions),
        HumanMessage(content=f"症状描述：{description}")
    ])

    # 尝试使用结构化输出
    try:
        logger.info("尝试使用结构化输出进行诊断")
        structured_llm = llm.with_structured_output(
            DiagnosisSchema, method="json_schema")
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
            logger.error(f"诊断调用完全失败: {e2}")
            logger.error(f"LLM 原始内容: {raw_response.content if 'raw_response' in locals() else 'N/A'}")

            # 返回错误而非默认建议（医学项目必须严谨）
            logger.warning("诊断LLM调用失败，不提供默认诊断建议以确保安全性")
            return {"diagnosis": []}

    # response should already be parsed into dict or a pydantic model matching DiagnosisSchema
    # Normalize and ensure types match VetAgentState expectations
    try:
        # If the structured output returned a pydantic BaseModel, convert to dict
        if hasattr(response, "model_dump"):
            response = response.model_dump()
            logger.debug(f"转换为字典: {list(response.keys()) if isinstance(response, dict) else type(response)}")

        diag_list = response.get("diagnosis") if isinstance(
            response, dict) else None
        if not isinstance(diag_list, list):
            # try to extract from nested structure
            logger.warning(f"diagnosis 字段不是列表: {type(diag_list)}, response={response}")
            diag_list = []

        normalized: List[DiagnosisItem] = []
        for item in diag_list:
            # item may already be a dict matching DiagnosisItem
            symptom = item.get("symptom", "")
            reason = item.get("reason", "")
            probability = float(item.get("probability", 0))
            normalized.append(DiagnosisItem(
                symptom=symptom, reason=reason, probability=probability))

        logger.info(f"成功规范化 {len(normalized)} 个诊断结果")
        # Return as a simple dict compatible with VetAgentState
        return {"diagnosis": normalized}
    except Exception as e:
        logger.error(f"诊断结果解析失败: {e}; raw={response}", exc_info=True)

        # 返回空列表而非默认建议（医学项目必须严谨，不能提供不准确的医疗建议）
        logger.warning("诊断结果解析失败，返回空列表以确保安全性")
        return {"diagnosis": []}
