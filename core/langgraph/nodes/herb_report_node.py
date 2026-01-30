"""
中医诊断报告节点 - 生成结构化中医诊断报告
"""
from datetime import datetime
from typing import List

from core.langgraph.state_herb import (
    HerbalPrescriptionItem,
    TCAgentState,
    TCMNursingItem,
    TCMZhengmingItem,
)


async def HerbReportNode(state: TCAgentState) -> dict:
    """生成中医诊断结构化报告

    Returns:
        dict compatible with TCAgentState
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.debug("HerbReportNode 执行 - 验证修复是否生效")
    description = getattr(state, "description",
                          "") or state.get("description", "")
    zhengming: List[TCMZhengmingItem] = getattr(
        state, "zhengming", []) or state.get("zhengming", []) or []
    prescriptions: List[HerbalPrescriptionItem] = getattr(
        state, "prescriptions", []) or state.get("prescriptions", []) or []

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"中医诊断报告生成时间: {now}"]

    if description:
        lines.append(f"症状描述: {description}")

    if zhengming:
        lines.append("\n## 中医证型诊断（按概率排序）:")
        for idx, z in enumerate(zhengming, start=1):
            name = getattr(z, "zhengming", "") or (
                z.get("zhengming") if isinstance(z, dict) else "")
            desc = getattr(z, "description", "") or (
                z.get("description") if isinstance(z, dict) else "")
            prob = getattr(z, "probability", None) or (
                z.get("probability") if isinstance(z, dict) else None)
            therapy = getattr(z, "therapy", "") or (
                z.get("therapy") if isinstance(z, dict) else "")
            prob_str = f"{float(prob):.3f}" if prob is not None else "-"
            lines.append(f"{idx}. {name} (置信度: {prob_str})")
            lines.append(f"   治法: {therapy}")
            if desc:
                lines.append(f"   辨证依据: {desc}")
    else:
        lines.append("\n未生成中医证型诊断。")

    if prescriptions:
        # 按证型分组
        from collections import defaultdict
        grouped = defaultdict(list)
        for p in prescriptions:
            p_zhengming = getattr(p, "zhengming", "") or (
                p.get("zhengming") if isinstance(p, dict) else "")
            grouped[p_zhengming].append(p)

        lines.append("\n## 中药方剂建议:")

        for zhengming_name, preds in grouped.items():
            lines.append(f"\n### 证型: {zhengming_name}")
            for idx, p in enumerate(preds, 1):
                ptype = getattr(p, "prescription_type", "") or (
                    p.get("prescription_type") if isinstance(p, dict) else "")
                pname = getattr(p, "prescription_name", "") or (
                    p.get("prescription_name") if isinstance(p, dict) else "")
                composition = getattr(p, "composition", "") or (
                    p.get("composition") if isinstance(p, dict) else "")
                usage = getattr(p, "usage", "") or (
                    p.get("usage") if isinstance(p, dict) else "")

                lines.append(f"{idx}. [{ptype}] {pname}")
                lines.append(f"   组成: {composition}")
                lines.append(f"   用法: {usage}")
    else:
        lines.append("\n未生成中药方剂建议。")

    # 中医声明和注意事项
    lines.append("\n" + "=" * 60)
    lines.append("重要声明")
    lines.append("=" * 60)
    lines.append("本报告为AI辅助生成的中医辨证论治建议，仅供参考。")
    lines.append("")
    lines.append("⚠️  安全提醒:")
    lines.append("1. 中医诊断需由专业中兽医进行四诊合参（望闻问切）")
    lines.append("2. 中药方剂需根据宠物体重、年龄、体质精确调整剂量")
    lines.append("3. 中药材需确保质量，炮制方法需规范")
    lines.append("4. 用药期间需密切观察病情变化，及时调整方药")
    lines.append("5. 急重症需中西医结合治疗，不要延误病情")
    lines.append("")
    lines.append("建议立即中西医结合就医的情况:")
    lines.append("- 持续呕吐腹泻超过24小时，伴有脱水")
    lines.append("- 高热不退，呼吸困难")
    lines.append("- 精神极度萎靡、昏迷或抽搐")
    lines.append("- 完全拒食超过48小时")
    lines.append("- 便血、尿血或呕血")
    lines.append("=" * 60)
    lines.append("")
    lines.append("【中医理论说明】")
    lines.append("中医强调整体观念和辨证论治，本报告基于症状描述进行辨证。")
    lines.append("实际临床应用中，建议结合中兽医的四诊合参，综合判断。")
    lines.append("")
    lines.append("【中药安全性】")
    lines.append("1. 使用正规渠道购买的中药材，确保质量")
    lines.append("2. 严格按照推荐剂量使用，不可随意加量")
    lines.append("3. 注意配伍禁忌（十八反、十九畏）")
    lines.append("4. 某些中药材有毒性，需专业炮制（如附子需先煎）")
    lines.append("5. 与西药同服时需间隔1-2小时")

    report = "\n".join(lines)

    # 详细调试：检查返回值
    logger.debug(f"HerbReportNode 准备返回 - zhengming type: {type(zhengming)}, len: {len(zhengming) if isinstance(zhengming, list) else 'N/A'}")
    if isinstance(zhengming, list) and len(zhengming) > 0:
        logger.debug(f"zhengming[0] type: {type(zhengming[0])}")

    # Return updated state-like dict
    return {
        "report": report,
        "zhengming": zhengming,
        "prescriptions": prescriptions
    }
