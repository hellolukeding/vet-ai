"""
用药安全检查节点 - 对药物建议进行安全性和合理性检查
"""

from datetime import datetime
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config.logger import logger
from core.langgraph.state import MedicationItem, VetAgentState
from core.llm_factory import create_chat_llm, invoke_json_model


class MedicationWithWarning(BaseModel):
    """带安全警告的药物"""

    symptom: str = Field(..., description="症状/诊断")
    drug_name: str = Field(..., description="药物名称")
    dosage: str = Field(..., description="剂量")
    frequency: str = Field(..., description="用药频率")
    safety_warning: str = Field(
        ..., description="该药物的安全警告（如果没有警告则返回'✅ 无特殊安全警告'）"
    )


class SafetyCheckSchema(BaseModel):
    """用药安全检查结果schema"""

    safe_medications: List[MedicationWithWarning] = Field(
        ..., description="通过安全检查的药物列表（每个药物包含安全警告）"
    )
    review_summary: str = Field(..., description="安全审查总结")


def _mark_unreviewed(medications: List[MedicationItem]) -> List[MedicationItem]:
    warning = "⚠️ AI安全审查未完成，必须由执业兽医核对适应证、剂量和禁忌后使用"
    return [
        MedicationItem(
            **{
                **(m.model_dump() if hasattr(m, "model_dump") else dict(m)),
                "safety_warning": warning,
            }
        )
        for m in medications
    ]


async def SafetyCheckNode(state: VetAgentState) -> Dict:
    """对药物建议进行安全检查和合理性验证

    Args:
        state: 包含 diagnosis 和 medications 的 VetAgentState

    Returns:
        dict with medications key (每个药物都包含对应的安全警告字段)
    """
    temperature = 0.2  # 低温度以确保安全检查的一致性

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 获取诊断和用药
    diagnosis = getattr(state, "diagnosis", []) or state.get("diagnosis", [])
    medications: List[MedicationItem] = getattr(state, "medications", []) or state.get(
        "medications", []
    )

    if not medications:
        logger.warning("安全检查：没有用药建议需要检查")
        return {"medications": []}

    try:
        llm = create_chat_llm(temperature=temperature)
    except Exception as e:
        logger.error(f"安全检查节点LLM初始化失败: {e}")
        logger.warning("安全检查LLM配置不可用，返回原始用药建议并标记未审查")
        return {"medications": _mark_unreviewed(medications)}

    # 构建诊断信息
    diagnosis_text = "诊断结果：\n"
    for d in diagnosis[:5]:  # 最多显示5个诊断
        symptom = getattr(d, "symptom", "") or (
            d.get("symptom") if isinstance(d, dict) else ""
        )
        prob = getattr(d, "probability", None) or (
            d.get("probability") if isinstance(d, dict) else 0
        )
        diagnosis_text += f"- {symptom} (概率: {prob})\n"

    # 构建用药信息
    med_text = "当前用药建议：\n"
    for idx, m in enumerate(medications, 1):
        symptom = getattr(m, "symptom", "") or (
            m.get("symptom") if isinstance(m, dict) else ""
        )
        drug = getattr(m, "drug_name", "") or (
            m.get("drug_name") if isinstance(m, dict) else ""
        )
        dosage = getattr(m, "dosage", "") or (
            m.get("dosage") if isinstance(m, dict) else ""
        )
        freq = getattr(m, "frequency", "") or (
            m.get("frequency") if isinstance(m, dict) else ""
        )
        med_text += f"{idx}. {drug} - {symptom}\n   剂量: {dosage}, 频率: {freq}\n"

    system_instructions = f"""
    当前时间：{current_time}
    你是一位兽医药学安全专家，负责审查用药建议的安全性和合理性。

    ## ⚠️ 核心原则
    1. **安全第一**：宁可保守，不可冒险
    2. **循证医学**：基于兽药标准和权威指南
    3. **明确警告**：任何潜在风险必须明确标注

    ## 安全检查项目

    ### 1. 剂量合理性检查
    - 剂量是否在安全范围内？
    - 单位是否正确（mg/kg vs mcg/kg）？
    - 给药途径是否合适？
    - 频率是否合理？

    ### 2. 药物-诊断匹配度
    - 药物是否适用于该诊断？
    - 是否有一线治疗药物优先？
    - 是否有不必要的药物？

    ### 3. 药物相互作用
    - 多药联用时是否有相互作用？
    - 是否有禁忌联用？

    ### 4. 特殊情况警示
    - 肾/肝功能不全时的药物禁忌
    - 妊娠/哺乳期慎用药物
    - 幼年/老年动物剂量调整
    - 品种特异性不良反应（如 Collie 犬对伊维菌素敏感）

    ### 5. 高风险药物识别
    - 治疗指数窄的药物（如地高辛）
    - 需要监测的药物（如氨基糖苷类）
    - 过敏风险高的药物

    ## 输出格式
    JSON: {{
      "safe_medications": [
        {{
          "symptom": "症状名称",
          "drug_name": "药物名称",
          "dosage": "剂量",
          "frequency": "频率",
          "safety_warning": "该药物的具体安全警告"
        }}
      ],
      "review_summary": "安全审查总结"
    }}

    ## safety_warning 字段示例
    - "⚠️ 氨基糖苷类有肾毒性风险，建议监测肾功能"
    - "⚠️ 地高辛治疗指数窄，需监测血药浓度"
    - "⚠️ 阿托品可能加重心动过速，慎用于心律失常患者"
    - "⚠️ 糖皮质激素可能影响伤口愈合，糖尿病动物慎用"
    - "⚠️ 恩诺沙星对幼年动物有软骨毒性风险"
    - "✅ 剂量在安全范围内，无明显禁忌"

    ## 审查原则
    - 为每个药物提供具体的安全警告
    - 如果用药合理且无特殊风险，返回 "✅ 剂量在安全范围内，无明显禁忌"
    - 如果发现安全问题，明确描述风险但不删除药物（让兽医判断）
    - review_summary 简要说明审查结果（最多200字）
    - 严格只输出 JSON，不要使用Markdown代码块
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_instructions),
            HumanMessage(content=diagnosis_text + "\n" + med_text),
        ]
    )

    try:
        logger.info("开始用药安全检查")
        messages = prompt.format_messages()
        validated = await invoke_json_model(llm, messages, SafetyCheckSchema)
        logger.info(f"安全检查完成: {validated.review_summary}")
        response_dict = validated.model_dump()

        safe_meds = response_dict.get("safe_medications", [])
        normalized = []
        for item in safe_meds:
            normalized.append(
                MedicationItem(
                    symptom=item.get("symptom", ""),
                    drug_name=item.get("drug_name", ""),
                    dosage=item.get("dosage", ""),
                    frequency=item.get("frequency", ""),
                    safety_warning=item.get("safety_warning", ""),
                )
            )

        logger.info(f"用药安全检查完成，{len(normalized)} 个药物通过检查")

        # 记录所有药物的安全警告
        logger.info("=" * 60)
        logger.info("安全检查报告")
        logger.info("=" * 60)
        for med in normalized:
            if med.safety_warning:
                logger.info(f"  {med.drug_name}: {med.safety_warning}")
        logger.info(f"  审查总结: {response_dict.get('review_summary', '')}")
        logger.info("=" * 60)

        return {"medications": normalized}

    except Exception as e:
        logger.warning(f"安全检查失败: {e}，保持原用药建议")
        # 安全检查失败时返回原用药，但记录警告
        logger.error("⚠️ 用药安全检查失败，建议由执业兽医人工审核所有用药")
        return {"medications": _mark_unreviewed(medications)}
