from langgraph.graph import END, START, StateGraph

from core.langgraph.nodes import call_model
from core.langgraph.nodes.diagnosis_node import DiagnosisNode
from core.langgraph.nodes.pharmacist_node import PharmacistNode
from core.langgraph.nodes.report_node import ReportNode
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
        """
        workflow = StateGraph(VetAgentState)
        # 负责提取信息
        # workflow.add_node("call_model", call_model)
        # 负责诊断病情
        workflow.add_node("DiagnosisNode", DiagnosisNode)
        # 负责最终结构化报告
        workflow.add_node("ReportNode", ReportNode)
        # 负责使用工具生成用药建议
        workflow.add_node("PharmacistNode", PharmacistNode)

        # 连接节点
        # workflow.add_edge(START, "call_model")
        # workflow.add_edge("call_model", "DiagnosisNode")
        workflow.add_edge(START, "DiagnosisNode")
        workflow.add_edge("DiagnosisNode", "PharmacistNode")
        workflow.add_edge("PharmacistNode", "ReportNode")
        workflow.add_edge("ReportNode", END)

        # graph
        self.graph = workflow.compile(
            checkpointer=None,
            interrupt_before=None,
            interrupt_after=None,
        )


graph = VetAgent().graph

__all__ = [
    "graph"
]
