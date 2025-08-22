

from datetime import datetime
from typing import List

from core.langgraph.state import DiagnosisItem, MedicationItem, VetAgentState


async def ReportNode(state: VetAgentState) -> VetAgentState:
    """Aggregate state into a human-readable structured report.

    Returns a dict compatible with VetAgentState. Adds a `report` key with a
    concise summary (string) while preserving `diagnosis` and `medications`.

    The report is deterministic and safe (no external calls).
    """
    description = getattr(state, "description",
                          "") or state.get("description", "")
    diagnosis: List[DiagnosisItem] = getattr(
        state, "diagnosis", []) or state.get("diagnosis", []) or []
    medications: List[MedicationItem] = getattr(
        state, "medications", []) or state.get("medications", []) or []

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"报告生成时间: {now}"]

    if description:
        lines.append(f"症状描述: {description}")

    if diagnosis:
        lines.append("\n初步诊断 (按可能性排序):")
        for idx, d in enumerate(diagnosis, start=1):
            # d may be pydantic model or dict-like
            name = getattr(d, "symptom", None) or (
                d.get("symptom") if isinstance(d, dict) else str(d))
            reason = getattr(d, "reason", None) or (
                d.get("reason") if isinstance(d, dict) else "")
            prob = getattr(d, "probability", None) or (
                d.get("probability") if isinstance(d, dict) else None)
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
                m.get("symptom") if isinstance(m, dict) else "")
            drug = getattr(m, "drug_name", None) or (
                m.get("drug_name") if isinstance(m, dict) else "")
            dosage = getattr(m, "dosage", None) or (
                m.get("dosage") if isinstance(m, dict) else "")
            freq = getattr(m, "frequency", None) or (
                m.get("frequency") if isinstance(m, dict) else "")
            parts = [p for p in [f"适应症: {symptom}" if symptom else "", f"药物: {drug}" if drug else "",
                                 f"剂量/用法: {dosage}" if dosage else "", f"频率: {freq}" if freq else ""] if p]
            lines.append(f"{idx}. " + "； ".join(parts))
    else:
        lines.append("\n未生成用药建议。")

    # Final short recommendations section
    lines.append("\n注意: 本报告为自动生成的汇总意见，仅供参考。具体处方与剂量请结合临床检查与体重并由有资质的兽医确认。")

    report = "\n".join(lines)

    # Return updated state-like dict so downstream nodes can read structured data
    return {"report": report, "diagnosis": diagnosis, "medications": medications}
