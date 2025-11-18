"""
最终输出节点

该节点负责整合所有信息，生成最终的结构化输出。
"""

from typing import Dict

from config.logger import logger
from core.plan.state import State


async def FinalOutputNode(state: State) -> Dict:
    """
    最终输出节点

    整合宠物信息、营养计划、护理计划和验证结果，
    生成最终的结构化输出，标记工作流完成。

    Args:
        state: 当前工作流状态，包含所有生成的计划

    Returns:
        Dict: 包含最终输出标志的字典
    """
    # 检查所有必要的计划是否都已生成
    nutrition_ready = state.flags.nutrition_plan_ready
    care_ready = state.flags.care_plan_ready

    # 生成摘要信息（可选，用于日志或调试）
    summary_lines = []

    if state.pet.name:
        summary_lines.append(f"为宠物 {state.pet.name} 生成了护理计划")
    else:
        summary_lines.append(f"为 {state.pet.species or '宠物'} 生成了护理计划")

    if nutrition_ready:
        summary_lines.append(
            f"✓ 营养计划：每日 {state.nutrition_plan.daily_calories}kcal")
        summary_lines.append(
            f"  - 推荐食物 {len(state.nutrition_plan.recommended_foods)} 项")
        summary_lines.append(
            f"  - 补充剂 {len(state.nutrition_plan.supplements)} 项")
    else:
        summary_lines.append("✗ 营养计划生成失败")

    if care_ready:
        summary_lines.append(f"✓ 护理计划：")
        summary_lines.append(f"  - 美容护理 {len(state.care_plan.grooming)} 项")
        summary_lines.append(f"  - 医疗护理 {len(state.care_plan.medical)} 项")
        summary_lines.append(f"  - 运动建议 {len(state.care_plan.exercise)} 项")
        summary_lines.append(f"  - 疫苗接种 {len(state.care_plan.vaccination)} 项")
    else:
        summary_lines.append("✗ 护理计划生成失败")

    # 添加风险分析摘要
    if state.reasoning.risk_analysis:
        summary_lines.append(f"\n风险评估：")
        # 只取第一行（通常是总结）
        first_line = state.reasoning.risk_analysis.split("\n")[0]
        summary_lines.append(f"  {first_line}")

    if state.reasoning.contradictions:
        summary_lines.append(
            f"\n发现 {len(state.reasoning.contradictions)} 个潜在问题需要注意")

    summary = "\n".join(summary_lines)
    logger.info("="*50)
    logger.info(summary)
    logger.info("="*50)

    # 标记最终输出已准备好
    final_ready = nutrition_ready and care_ready

    if final_ready:
        logger.info("【FinalOutputNode】所有计划生成完成")
    else:
        logger.warning("【FinalOutputNode】部分计划生成失败")

    return {
        "flags": {
            "final_output_ready": final_ready
        }
    }
