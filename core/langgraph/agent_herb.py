"""
中医诊断 LangGraph 工作流
"""

from langgraph.graph import END, START, StateGraph

from core.langgraph.nodes.herb_diagnosis_node import HerbDiagnosisNode
from core.langgraph.nodes.herb_literature_node import HerbLiteratureSearchNode
from core.langgraph.nodes.herb_nursing_node import HerbNursingNode
from core.langgraph.nodes.herb_pharmacist_node import HerbPharmacistNode
from core.langgraph.nodes.herb_report_node import HerbReportNode
from core.langgraph.state_herb import TCAgentState


class HerbAgent:
    def __init__(self):
        """
        初始化中医诊断代理。
        """
        self.graph = None
        self._build_workflow()

    def _build_workflow(self):
        """
        构建中医诊断工作流。

        工作流顺序：
        1. HerbLiteratureSearchNode - 搜索中医文献
        2. HerbDiagnosisNode - 中医辨证论治
        3. HerbPharmacistNode - 推荐中药方剂
        4. HerbNursingNode - 生成护理建议
        5. HerbReportNode - 生成最终报告
        """
        workflow = StateGraph(TCAgentState)

        # 步骤1: 中医文献搜索（辨证前）
        workflow.add_node("HerbLiteratureSearchNode", HerbLiteratureSearchNode)
        # 步骤2: 中医辨证论治
        workflow.add_node("HerbDiagnosisNode", HerbDiagnosisNode)
        # 步骤3: 推荐中药方剂
        workflow.add_node("HerbPharmacistNode", HerbPharmacistNode)
        # 步骤4: 生成护理建议
        workflow.add_node("HerbNursingNode", HerbNursingNode)
        # 步骤5: 生成最终结构化报告
        workflow.add_node("HerbReportNode", HerbReportNode)

        # 连接节点
        workflow.add_edge(START, "HerbLiteratureSearchNode")
        workflow.add_edge("HerbLiteratureSearchNode", "HerbDiagnosisNode")
        workflow.add_edge("HerbDiagnosisNode", "HerbPharmacistNode")
        workflow.add_edge("HerbPharmacistNode", "HerbNursingNode")
        workflow.add_edge("HerbNursingNode", "HerbReportNode")
        workflow.add_edge("HerbReportNode", END)

        # 编译工作流
        self.graph = workflow.compile(
            checkpointer=None,
            interrupt_before=None,
            interrupt_after=None,
        )


herb_graph = HerbAgent().graph

__all__ = ["herb_graph"]
