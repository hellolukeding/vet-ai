from langgraph.graph import END, START, StateGraph

from core.langgraph.nodes.diagnosis_node import DiagnosisNode
from core.langgraph.nodes.diagnosis_review_node import DiagnosisReviewNode
from core.langgraph.nodes.literature_search_node import LiteratureSearchNode
from core.langgraph.nodes.pharmacist_node import PharmacistNode
from core.langgraph.nodes.report_node import ReportNode
from core.langgraph.nodes.safety_check_node import SafetyCheckNode
from core.langgraph.state import VetAgentState


class VetAgent:
    def __init__(self):
        """
        初始化诊断代理。
        """
        self.graph = None
        self._build_workflow()

    def _build_workflow(self):
        """
        构建工作流。

        工作流顺序：
        1. LiteratureSearchNode - 搜索医学文献
        2. DiagnosisNode - 生成诊断结果
        3. DiagnosisReviewNode - 审查诊断质量
        4. PharmacistNode - 生成用药建议
        5. SafetyCheckNode - 检查用药安全
        6. ReportNode - 生成最终报告
        """
        workflow = StateGraph(VetAgentState)
        # 负责提取信息
        # workflow.add_node("call_model", call_model)

        # 步骤1: 文献搜索（诊断前）
        workflow.add_node("LiteratureSearchNode", LiteratureSearchNode)
        # 步骤2: 诊断病情
        workflow.add_node("DiagnosisNode", DiagnosisNode)
        # 步骤3: 诊断审查（质量保证）
        workflow.add_node("DiagnosisReviewNode", DiagnosisReviewNode)
        # 步骤4: 生成用药建议
        workflow.add_node("PharmacistNode", PharmacistNode)
        # 步骤5: 用药安全检查
        workflow.add_node("SafetyCheckNode", SafetyCheckNode)
        # 步骤6: 生成最终结构化报告
        workflow.add_node("ReportNode", ReportNode)

        # 连接节点
        # workflow.add_edge(START, "call_model")
        # workflow.add_edge("call_model", "DiagnosisNode")
        workflow.add_edge(START, "LiteratureSearchNode")
        workflow.add_edge("LiteratureSearchNode", "DiagnosisNode")
        workflow.add_edge("DiagnosisNode", "DiagnosisReviewNode")
        workflow.add_edge("DiagnosisReviewNode", "PharmacistNode")
        workflow.add_edge("PharmacistNode", "SafetyCheckNode")
        workflow.add_edge("SafetyCheckNode", "ReportNode")
        workflow.add_edge("ReportNode", END)

        # graph
        self.graph = workflow.compile(
            checkpointer=None,
            interrupt_before=None,
            interrupt_after=None,
        )


graph = VetAgent().graph

__all__ = ["graph"]
