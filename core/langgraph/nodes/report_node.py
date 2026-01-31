from datetime import datetime
from typing import List

from core.langgraph.state import DiagnosisItem, MedicationItem, VetAgentState


async def ReportNode(state: VetAgentState) -> VetAgentState:
    """Aggregate state into a human-readable structured report.

    Returns a dict compatible with VetAgentState. Adds a `report` key with a
    concise summary (string) while preserving `diagnosis` and `medications`.

    The report is deterministic and safe (no external calls).
    """
    description = getattr(state, "description", "") or state.get("description", "")
    diagnosis: List[DiagnosisItem] = (
        getattr(state, "diagnosis", []) or state.get("diagnosis", []) or []
    )
    medications: List[MedicationItem] = (
        getattr(state, "medications", []) or state.get("medications", []) or []
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"报告生成时间: {now}"]

    if description:
        lines.append(f"症状描述: {description}")

    if diagnosis:
        lines.append("\n初步诊断 (按可能性排序):")
        for idx, d in enumerate(diagnosis, start=1):
            # d may be pydantic model or dict-like
            name = getattr(d, "symptom", None) or (
                d.get("symptom") if isinstance(d, dict) else str(d)
            )
            reason = getattr(d, "reason", None) or (
                d.get("reason") if isinstance(d, dict) else ""
            )
            prob = getattr(d, "probability", None) or (
                d.get("probability") if isinstance(d, dict) else None
            )
            prob_str = f"{float(prob):.3f}" if prob is not None else "-"
            lines.append(f"{idx}. {name} (概率: {prob_str})")
            if reason:
                # keep reason short
                lines.append(f"   依据: {reason}")
    else:
        lines.append("\n未生成诊断建议。")

    if medications:
        lines.append("\n用药建议:")
        for idx, m in enumerate(medications, start=1):
            symptom = getattr(m, "symptom", None) or (
                m.get("symptom") if isinstance(m, dict) else ""
            )
            drug = getattr(m, "drug_name", None) or (
                m.get("drug_name") if isinstance(m, dict) else ""
            )
            dosage = getattr(m, "dosage", None) or (
                m.get("dosage") if isinstance(m, dict) else ""
            )
            freq = getattr(m, "frequency", None) or (
                m.get("frequency") if isinstance(m, dict) else ""
            )
            parts = [
                p
                for p in [
                    f"适应症: {symptom}" if symptom else "",
                    f"药物: {drug}" if drug else "",
                    f"剂量/用法: {dosage}" if dosage else "",
                    f"频率: {freq}" if freq else "",
                ]
                if p
            ]
            lines.append(f"{idx}. " + "； ".join(parts))
    else:
        lines.append("\n未生成用药建议。")

    # Final short recommendations section
    lines.append("\n" + "=" * 60)
    lines.append("重要声明")
    lines.append("=" * 60)
    lines.append(
        "本报告为AI辅助生成的初步诊断和建议，仅供兽医参考，不能替代专业兽医的诊断和治疗。"
    )
    lines.append("")
    lines.append("⚠️  安全提醒:")
    lines.append("1. 本系统不能替代现场兽医临床诊断")
    lines.append("2. 所有用药方案必须由执业兽医根据实际情况确认")
    lines.append("3. 剂量需根据宠物体重、年龄、健康状况精确计算")
    lines.append("4. 紧急情况请立即就医，不要依赖本系统")
    lines.append("")
    lines.append("建议立即就医的情况:")
    lines.append("- 持续呕吐超过24小时")
    lines.append("- 伴有腹泻、便血或呕血")
    lines.append("- 体温异常（发热或体温过低）")
    lines.append("- 精神极度萎靡、昏迷或抽搐")
    lines.append("- 无法进食或饮水超过24小时")
    lines.append("=" * 60)

    report = "\n".join(lines)

    # Return updated state-like dict so downstream nodes can read structured data
    return {"report": report, "diagnosis": diagnosis, "medications": medications}
