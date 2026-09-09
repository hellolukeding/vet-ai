from datetime import datetime
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config.logger import logger
from core.langgraph.state import DiagnosisItem, VetAgentState
from core.llm_factory import create_chat_llm, invoke_json_model


class DiagnosisSchema(BaseModel):
    """Expected structured output from the LLM.

    diagnosis: a list of diagnosis items. Each item must contain:
      - symptom: the name of the suspected disease/diagnosis
      - reason: a short rationale citing the key symptoms/evidence
      - probability: a float between 0 and 1 indicating likelihood
    """

    diagnosis: List[DiagnosisItem] = Field(..., max_length=5, description="诊断列表")


async def DiagnosisNode(state: VetAgentState) -> Dict[str, List[DiagnosisItem]]:
    """Generate diagnostic suggestions from `state.description` and return a VetAgentState-like dict.

    Contract:
      - input: state with `description: str` (one-line pet symptom description)
      - output: dict matching VetAgentState with `diagnosis: list[DiagnosisItem]`
    """

    temperature = 0.6

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    description = getattr(state, "description", "") or state.get("description", "")

    if not description:
        return {"diagnosis": []}

    try:
        llm = create_chat_llm(temperature=temperature)
    except Exception as e:
        logger.error(f"诊断节点LLM初始化失败: {e}")
        logger.warning("诊断LLM配置不可用，不提供默认诊断建议以确保安全性")
        return {"diagnosis": []}

    # Clear, precise system prompt to encourage exact JSON output matching DiagnosisSchema
    system_instructions = f"""
    当前时间：{current_time}
    你是一位资深兽医（中文输出），对小动物临床表现、鉴别诊断和常用处方非常熟悉。

    ## 任务
    根据症状描述和医学文献参考，列出最多5个有依据的鉴别诊断。信息不足时可以少于5个，不得为了凑数添加低质量诊断。返回严格的JSON，不要包含额外的文本。

    ## 推理步骤（Chain of Thought）
    1. **症状分析**：提取关键症状、体征、病史信息
    2. **初步鉴别**：根据症状列出可能的疾病谱
    3. **文献参考**：如果有提供的文献，参考其中的医学知识
    4. **概率评估**：综合症状匹配度、发病率、文献证据，评估每个诊断的可能性
    5. **依据总结**：为每个诊断提供简洁的医学依据

    ## 输出格式
    JSON schema: {{"diagnosis": [{{"symptom": str, "reason": str, "probability": float}}]}}

    ## 诊断示例
    症状："2岁哈士奇，体温30°C，心率40次/分，呕吐不进食"
    推理过程：
    - 严重低体温（30°C）+ 心动过缓（40次/分）→ 提示中枢神经系统抑制或内分泌危象
    - 呕吐不进食 → 消化道症状或中毒表现
    - 哈士奇品种 → 异物吞食风险高
    - 年轻成年犬 → 肾上腺皮质功能减退好发年龄

    期望输出：
    {{
      "diagnosis": [
        {{"symptom": "阿片类药物或镇静剂中毒", "reason": "严重低体温（30°C）和心动过缓（40次/分）是中枢神经系统抑制的典型体征；呕吐常见于中毒早期；哈士奇有误食风险。", "probability": 0.35}},
        {{"symptom": "肾上腺皮质功能减退危象", "reason": "常见于年轻成年犬；呕吐和厌食为典型前驱症状；高钾血症导致心动过缓，休克引起严重低体温。", "probability": 0.25}},
        {{"symptom": "胃肠梗阻伴休克", "reason": "哈士奇易发生异物吞食；呕吐不进食为消化道典型症状；严重梗阻导致继发性休克，表现为低体温和心率异常。", "probability": 0.20}},
        {{"symptom": "严重环境性低体温", "reason": "体温30°C为极低值，直接导致窦房结抑制引起心动过缓；呕吐可能继发于低温导致的胃肠动力减弱。", "probability": 0.12}},
        {{"symptom": "III度房室传导阻滞", "reason": "心率仅40次/分提示严重的心动过缓；心输出量不足导致外周灌注不良及低体温；呕吐可能继发于组织低灌注。", "probability": 0.08}}
      ]
    }}

    ## 要求
      - 最多输出5个诊断结果，按可能性从高到低排序；没有足够依据时减少数量
      - 每个诊断的 `symptom` 字段写疾病或综合征的简短名称（中文）
      - `reason` 必须基于症状提供医学依据，引用具体症状/体征/病史要点（2-3项）
      - `probability` 为 0 到 1 的小数，三位小数精度优先，总和不用严格为1，但请确保相对合理
      - 如果有提供的文献参考，请结合文献内容进行诊断推理
      - 不要返回诊断以外的段落说明或解释文本，严格只输出 JSON
      - 不要使用任何Markdown代码块格式（如```json）包装结果
    """

    # 构建包含文献参考的prompt
    human_content = f"症状描述：{description}"

    # 如果有文献参考，添加到prompt中
    literature: List = getattr(state, "literature", []) or state.get("literature", [])
    if literature:
        human_content += "\n\n## 医学文献参考\n"
        for idx, lit in enumerate(literature[:5], 1):  # 最多参考5条
            title = getattr(lit, "title", "") or (
                lit.get("title") if isinstance(lit, dict) else ""
            )
            snippet = getattr(lit, "snippet", "") or (
                lit.get("snippet") if isinstance(lit, dict) else ""
            )
            content = getattr(lit, "content", "") or (
                lit.get("content") if isinstance(lit, dict) else ""
            )

            human_content += f"\n文献{idx}：{title}\n"
            if snippet:
                human_content += f"摘要：{snippet}\n"
            if content and len(content) > 100:
                human_content += f"内容摘要：{content[:300]}...\n"
        logger.info(f"诊断节点使用 {len(literature)} 条文献参考")

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_instructions),
            HumanMessage(content=human_content),
        ]
    )

    try:
        messages = prompt.format_messages()
        response = (
            await invoke_json_model(llm, messages, DiagnosisSchema)
        ).model_dump()
    except Exception as e:
        logger.error(f"诊断调用失败: {e}")
        logger.warning("诊断LLM调用失败，不提供默认诊断建议以确保安全性")
        return {"diagnosis": []}

    # response should already be parsed into dict or a pydantic model matching DiagnosisSchema
    # Normalize and ensure types match VetAgentState expectations
    try:
        # If the structured output returned a pydantic BaseModel, convert to dict
        if hasattr(response, "model_dump"):
            response = response.model_dump()
            logger.debug(
                f"转换为字典: {list(response.keys()) if isinstance(response, dict) else type(response)}"
            )

        diag_list = response.get("diagnosis") if isinstance(response, dict) else None
        if not isinstance(diag_list, list):
            # try to extract from nested structure
            logger.warning(
                f"diagnosis 字段不是列表: {type(diag_list)}, response={response}"
            )
            diag_list = []

        normalized: List[DiagnosisItem] = []
        for item in diag_list:
            # item may already be a dict matching DiagnosisItem
            symptom = item.get("symptom", "")
            reason = item.get("reason", "")
            probability = float(item.get("probability", 0))
            normalized.append(
                DiagnosisItem(symptom=symptom, reason=reason, probability=probability)
            )

        logger.info(f"成功规范化 {len(normalized)} 个诊断结果")
        # Return as a simple dict compatible with VetAgentState
        return {"diagnosis": normalized}
    except Exception as e:
        logger.error(f"诊断结果解析失败: {e}; raw={response}", exc_info=True)

        # 返回空列表而非默认建议（医学项目必须严谨，不能提供不准确的医疗建议）
        logger.warning("诊断结果解析失败，返回空列表以确保安全性")
        return {"diagnosis": []}
