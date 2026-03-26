"""
诊断审查节点 - 对诊断结果进行质量审查和优化
"""

from datetime import datetime
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config.logger import logger
from core.langgraph.state import DiagnosisItem, VetAgentState
from core.llm_factory import create_chat_llm


class DiagnosisReviewSchema(BaseModel):
    """诊断审查结果schema"""

    reviewed_diagnosis: List[DiagnosisItem] = Field(..., description="审查后的诊断列表")
    review_notes: str = Field(..., description="审查意见和改进说明")


async def DiagnosisReviewNode(state: VetAgentState) -> Dict[str, List[DiagnosisItem]]:
    """对诊断结果进行质量审查，确保诊断的合理性和完整性

    Args:
        state: 包含 diagnosis 和 literature 的 VetAgentState

    Returns:
        dict with reviewed_diagnosis key
    """
    temperature = 0.3  # 降低温度以获得更一致的审查结果

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 获取诊断和文献
    diagnosis: List[DiagnosisItem] = getattr(state, "diagnosis", []) or state.get(
        "diagnosis", []
    )
    literature: List = getattr(state, "literature", []) or state.get("literature", [])

    if not diagnosis:
        logger.warning("诊断审查：没有诊断结果需要审查")
        return {"reviewed_diagnosis": []}

    try:
        llm = create_chat_llm(temperature=temperature)
    except Exception as e:
        logger.error(f"诊断审查节点LLM初始化失败: {e}")
        logger.warning("诊断审查LLM配置不可用，跳过审查")
        return {"reviewed_diagnosis": diagnosis}

    # 构建诊断信息
    diagnosis_text = "当前诊断结果：\n"
    for idx, d in enumerate(diagnosis, 1):
        symptom = getattr(d, "symptom", "") or (
            d.get("symptom") if isinstance(d, dict) else ""
        )
        reason = getattr(d, "reason", "") or (
            d.get("reason") if isinstance(d, dict) else ""
        )
        prob = getattr(d, "probability", None) or (
            d.get("probability") if isinstance(d, dict) else 0
        )
        diagnosis_text += f"{idx}. {symptom} (概率: {prob})\n   依据: {reason}\n"

    # 构建文献参考信息
    lit_text = ""
    if literature:
        lit_text = "\n医学文献参考：\n"
        for idx, lit in enumerate(literature[:3], 1):
            title = getattr(lit, "title", "") or (
                lit.get("title") if isinstance(lit, dict) else ""
            )
            snippet = getattr(lit, "snippet", "") or (
                lit.get("snippet") if isinstance(lit, dict) else ""
            )
            lit_text += (
                f"{idx}. {title}\n   {snippet[:200]}...\n"
                if snippet
                else f"{idx}. {title}\n"
            )

    system_instructions = f"""
    当前时间：{current_time}
    你是一位兽医临床专家，负责审查和优化诊断结果。

    ## 任务
    对提供的诊断结果进行质量审查，确保：
    1. **诊断合理性**：诊断是否基于症状和医学证据
    2. **概率一致性**：概率评估是否合理（总和约0.8-1.2为佳，最高不超过1.5）
    3. **依据充分性**：每个诊断是否有明确的医学依据
    4. **鉴别诊断完整性**：是否覆盖了主要可能性

    ## 审查步骤
    1. 逐一检查每个诊断的医学依据是否充分
    2. 评估概率分布是否合理
    3. 识别遗漏的重要鉴别诊断
    4. 修正明显不合理的诊断
    5. 优化诊断描述和依据

    ## 输出格式
    JSON: {{"reviewed_diagnosis": [{{"symptom": str, "reason": str, "probability": float}}], "review_notes": str}}

    ## 审查原则
    - 保持医学严谨性，不要添加无依据的诊断
    - 如果原诊断合理，保持不变
    - 如果发现明显错误，进行修正
    - review_notes 简要说明审查过程和修改原因
    - 严格只输出 JSON，不要使用Markdown代码块
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_instructions),
            HumanMessage(content=diagnosis_text + lit_text),
        ]
    )

    try:
        logger.info("开始诊断审查")
        structured_llm = llm.with_structured_output(
            DiagnosisReviewSchema, method="json_schema"
        )
        messages = prompt.format_messages()
        response = await structured_llm.ainvoke(messages)
        logger.info(f"诊断审查成功: {response.review_notes}")

        # 转换为标准格式
        if hasattr(response, "model_dump"):
            response = response.model_dump()

        reviewed = response.get("reviewed_diagnosis", [])
        normalized = []
        for item in reviewed:
            normalized.append(
                DiagnosisItem(
                    symptom=item.get("symptom", ""),
                    reason=item.get("reason", ""),
                    probability=float(item.get("probability", 0)),
                )
            )

        logger.info(f"诊断审查完成，审查后 {len(normalized)} 个诊断")
        return {"diagnosis": normalized}

    except Exception as e:
        logger.warning(f"诊断审查失败: {e}，保持原诊断结果")
        # 审查失败时返回原诊断，确保系统可用性
        return {"diagnosis": diagnosis}
