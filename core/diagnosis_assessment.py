"""Shared emergency, examination and first-aid assessment for diagnosis APIs."""

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field

from config.logger import logger
from core.llm_factory import create_chat_llm, invoke_json_model

AssessmentStatus = Literal["pending", "completed", "unavailable"]


class EmergencyAssessment(BaseModel):
    status: AssessmentStatus = "completed"
    level: Literal["emergency", "urgent", "routine", "unknown"] = "unknown"
    reasons: list[str] = Field(min_length=1)
    action: str = Field(min_length=1)
    missing_information: list[str] = Field(min_length=1)


class RecommendedTest(BaseModel):
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    priority: Literal["urgent", "recommended", "conditional"]
    related_findings: list[str] = Field(min_length=1)
    condition: str = Field(min_length=1)


class RecommendedTests(BaseModel):
    status: AssessmentStatus = "completed"
    items: list[RecommendedTest] = Field(min_length=1)


class TemporaryCare(BaseModel):
    status: AssessmentStatus = "completed"
    actions: list[str] = Field(min_length=1)
    avoid: list[str] = Field(min_length=1)
    escalation_signs: list[str] = Field(min_length=1)


class DiagnosisAssessment(BaseModel):
    status: Literal["pending", "completed", "partial", "unavailable"] = "completed"
    emergency: EmergencyAssessment
    recommended_tests: RecommendedTests
    temporary_care: TemporaryCare
    warnings: list[str] = Field(min_length=1)


class GeneratedEmergencyAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Literal["emergency", "urgent", "routine", "unknown"]
    reasons: list[str] = Field(min_length=1, max_length=5)
    action: str = Field(min_length=1)
    missing_information: list[str] = Field(min_length=1, max_length=6)


class GeneratedRecommendedTests(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RecommendedTest] = Field(min_length=1, max_length=5)


class GeneratedTemporaryCare(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actions: list[str] = Field(min_length=1, max_length=3)
    avoid: list[str] = Field(min_length=1, max_length=4)
    escalation_signs: list[str] = Field(min_length=1, max_length=5)


class GeneratedDiagnosisAssessment(BaseModel):
    """Strict model output; public status fields are added by the server."""

    model_config = ConfigDict(extra="forbid")

    emergency: GeneratedEmergencyAssessment
    recommended_tests: GeneratedRecommendedTests
    temporary_care: GeneratedTemporaryCare
    warnings: list[str] = Field(min_length=1, max_length=5)


def pending_assessment() -> dict:
    return DiagnosisAssessment(
        status="pending",
        emergency=EmergencyAssessment(
            status="pending",
            level="unknown",
            reasons=["正在分析症状和危险信号"],
            action="评估完成前请持续观察宠物；如出现呼吸困难、意识异常或大出血，请立即急诊",
            missing_information=["评估结果正在生成"],
        ),
        recommended_tests=RecommendedTests(
            status="pending",
            items=[
                RecommendedTest(
                    name="检查建议生成中",
                    purpose="根据症状确定需要优先排查的项目",
                    priority="conditional",
                    related_findings=["当前症状描述"],
                    condition="等待评估完成",
                )
            ],
        ),
        temporary_care=TemporaryCare(
            status="pending",
            actions=["保持宠物安静并持续观察呼吸和意识状态"],
            avoid=["不要自行喂药或进行侵入性处置"],
            escalation_signs=["呼吸困难、意识异常、持续抽搐、大出血或迅速恶化"],
        ),
        warnings=["评估正在生成，本结果暂不能替代执业兽医判断"],
    ).model_dump()


def unavailable_assessment() -> dict:
    return DiagnosisAssessment(
        status="unavailable",
        emergency=EmergencyAssessment(
            status="unavailable",
            level="unknown",
            reasons=["自动评估服务暂时不可用，无法可靠判断紧急程度"],
            action="请直接联系执业兽医；如出现危险信号请立即前往急诊",
            missing_information=["需要由执业兽医补充分诊和体格检查"],
        ),
        recommended_tests=RecommendedTests(
            status="unavailable",
            items=[
                RecommendedTest(
                    name="执业兽医现场评估",
                    purpose="补充生命体征、病史和体格检查后决定具体检查项目",
                    priority="urgent",
                    related_findings=["自动检查建议暂时不可用"],
                    condition="尽快联系兽医确定",
                )
            ],
        ),
        temporary_care=TemporaryCare(
            status="unavailable",
            actions=["保持宠物安静并尽快联系执业兽医"],
            avoid=["不要自行喂药、催吐或强行喂食"],
            escalation_signs=["呼吸困难、意识异常、持续抽搐、大出血或迅速恶化"],
        ),
        warnings=["评估服务暂时不可用，请直接咨询执业兽医；如情况紧急请立即就医。"],
    ).model_dump()


async def generate_assessment(description: str) -> dict:
    """Generate additive advice without changing either diagnosis workflow."""
    instructions = """
你是执业兽医分诊助手。仅根据用户明确提供的信息，生成紧急情况识别、建议检查项目和就医前临时处置建议。

要求：
1. 紧急程度只能是 emergency、urgent、routine、unknown。
   信息不足时使用 unknown，并列出缺失信息；没有缺失信息时填写“无”；routine 不代表已排除疾病。
2. reasons 必须引用输入中的事实，不得虚构体温、病史或检查结果。
3. 检查项目按 urgent、recommended、conditional 排序，最多5项，合并重复项目；
   condition 仅填写执行条件；没有附加条件时填写“无附加条件”。至少返回1项检查建议。
4. 临时处置仅限安全的就医前措施，不给出处方药剂量、侵入性操作、喂药、
   催吐或替代就医的建议。
5. 出现呼吸困难、意识障碍、持续抽搐、大出血、休克表现、中毒或其他危及
   生命迹象时，明确建议立即急诊。
6. 紧急病例不要建议喂食或饮水；信息不足时只建议安静观察、记录症状和联系
   兽医，不要建议禁食、改变饮食或触摸检查宠物。
7. actions 最多3项，avoid 最多4项，escalation_signs 最多5项，
   每项至少1条，每条只写一个简短、可执行的要点。
8. 所有字符串必须有实际内容，所有数组至少包含1项，禁止空字符串、空数组和 null。
9. warnings 至少包含“本评估仅供辅助，不能替代执业兽医诊断”。
10. 所有内容使用中文，严格返回下面形状的 JSON，不得更名、增加顶层字段或使用 Markdown：
{
  "emergency": {
    "level": "emergency|urgent|routine|unknown",
    "reasons": ["判断依据"],
    "action": "行动建议",
    "missing_information": ["缺失信息"]
  },
  "recommended_tests": {
    "items": [{
      "name": "检查名称",
      "purpose": "检查目的",
      "priority": "urgent|recommended|conditional",
      "related_findings": ["相关症状或发现"],
      "condition": "执行条件，没有则填写无附加条件"
    }]
  },
  "temporary_care": {
    "actions": ["可执行措施"],
    "avoid": ["应避免事项"],
    "escalation_signs": ["升级就医指征"]
  },
  "warnings": ["本评估仅供辅助，不能替代执业兽医诊断"]
}
""".strip()
    try:
        llm = create_chat_llm(temperature=0.1)
        generated = await invoke_json_model(
            llm,
            [
                SystemMessage(content=instructions),
                HumanMessage(content=f"症状描述：{description}"),
            ],
            GeneratedDiagnosisAssessment,
        )
        return DiagnosisAssessment(
            status="completed",
            emergency=EmergencyAssessment(
                status="completed", **generated.emergency.model_dump()
            ),
            recommended_tests=RecommendedTests(
                status="completed", **generated.recommended_tests.model_dump()
            ),
            temporary_care=TemporaryCare(
                status="completed", **generated.temporary_care.model_dump()
            ),
            warnings=generated.warnings,
        ).model_dump()
    except Exception as exc:
        logger.opt(exception=True).error("附加诊疗评估生成失败: {}", repr(exc))
        return unavailable_assessment()
