"""
宠物护理计划代理模块

该模块实现了基于LangGraph的宠物护理计划生成代理，
通过多个节点协同工作，生成结构化的营养计划和护理计划。
"""

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from config.logger import logger
from core.plan.nodes.care_node import CareNode
from core.plan.nodes.final_output_node import FinalOutputNode
from core.plan.nodes.nutrition_node import NutritionNode
from core.plan.nodes.pet_info_node import PetInfoNode
from core.plan.nodes.validator_node import ValidatorNode
from core.plan.state import State


class PetCareAgent:
    """
    宠物护理计划生成代理

    使用LangGraph构建多节点工作流，自动化生成宠物的营养计划和护理计划。

    工作流节点:
        1. PetInfoNode: 提取和补全宠物基本信息
        2. NutritionNode: 生成营养计划
        3. CareNode: 生成护理计划
        4. ValidatorNode: 验证计划的一致性和安全性
        5. FinalOutputNode: 生成最终结构化输出

    Attributes:
        graph: 编译后的LangGraph工作流图
    """

    def __init__(self, enable_validation: bool = True):
        """
        初始化宠物护理计划代理

        自动构建并编译工作流图。

        Args:
            enable_validation: 是否启用验证节点（默认True以确保完整性和安全性）
                              True: 运行完整验证，耗时约1.5分钟
                              False: 跳过验证，提升响应速度
        """
        self.enable_validation = enable_validation
        self.graph = None
        self._build_workflow()

    def _build_workflow(self):
        """
        构建LangGraph工作流

        创建状态图并添加所有节点和边，定义节点间的执行顺序和条件路由。

        性能优化：
        - nutrition和care节点并行执行
        - validator节点可选（通过enable_validation控制）
        """
        # 创建状态图
        workflow = StateGraph(State)

        # 添加同步等待节点 - 确保两个计划都完成
        async def wait_for_plans(state: State) -> Dict:
            """等待节点：不做任何操作，只是等待两个计划完成"""
            logger.debug(
                f"等待节点检查 - 营养: {state.flags.nutrition_plan_ready}, 护理: {state.flags.care_plan_ready}")
            return {}

        # 添加节点
        workflow.add_node("pet_info", PetInfoNode)
        workflow.add_node("nutrition", NutritionNode)
        workflow.add_node("care", CareNode)
        workflow.add_node("wait", wait_for_plans)

        # 根据配置决定是否添加验证节点
        if self.enable_validation:
            workflow.add_node("validator", ValidatorNode)
            logger.info("验证节点已启用（默认模式，确保完整性和安全性）")
        else:
            logger.info("验证节点已禁用（快速模式，跳过验证步骤）")

        workflow.add_node("final_output", FinalOutputNode)

        # 定义工作流路径
        # START -> 提取宠物信息
        workflow.add_edge(START, "pet_info")

        # 宠物信息 -> 并行生成营养计划和护理计划（性能优化）
        # 注意：每个节点内部都有速率限制器（max_concurrent=1），确保不会超过API并发限制
        # 并行执行可以节省约1.5分钟时间
        workflow.add_edge("pet_info", "nutrition")
        workflow.add_edge("pet_info", "care")

        # 两个计划都完成后进入等待节点
        workflow.add_edge("nutrition", "wait")
        workflow.add_edge("care", "wait")

        # 等待节点 -> 验证节点（可选）或直接到最终输出
        if self.enable_validation:
            workflow.add_edge("wait", "validator")
            workflow.add_edge("validator", "final_output")
        else:
            workflow.add_edge("wait", "final_output")

        # 最终输出 -> 结束
        workflow.add_edge("final_output", END)

        # 编译工作流
        self.graph = workflow.compile(
            checkpointer=None,
            interrupt_before=None,
            interrupt_after=None,
        )

    async def run(self, user_query: str, pet_info: Dict[str, Any] = None) -> State:
        """
        运行宠物护理计划生成流程

        Args:
            user_query: 用户查询或需求描述
            pet_info: 可选的宠物初始信息字典

        Returns:
            State: 包含完整营养和护理计划的状态对象

        Example:
            >>> agent = PetCareAgent()
            >>> result = await agent.run(
            ...     user_query="帮我的金毛制定营养和护理计划",
            ...     pet_info={"name": "Lucky", "age": "3 years", "weight": 30.0}
            ... )
            >>> print(result.nutrition_plan.daily_calories)
            >>> print(result.care_plan.exercise)
        """
        # 初始化状态
        initial_state = State(user_query=user_query)

        # 如果提供了宠物信息，更新状态
        if pet_info:
            for key, value in pet_info.items():
                if hasattr(initial_state.pet, key):
                    setattr(initial_state.pet, key, value)

        logger.info("开始执行宠物护理计划工作流")
        logger.debug(f"用户查询: {user_query}")
        if pet_info:
            logger.debug(f"初始宠物信息: {pet_info}")

        # 执行工作流 - LangGraph返回字典，需要转换为State对象
        final_state_dict = await self.graph.ainvoke(initial_state)

        logger.info("工作流执行完成")
        logger.debug(f"返回类型: {type(final_state_dict)}")

        # 将字典转换为State对象 - 使用from_dict方法正确处理嵌套对象
        if isinstance(final_state_dict, dict):
            logger.debug("使用from_dict转换字典为State对象")
            final_state = State.from_dict(final_state_dict)
        else:
            final_state = final_state_dict

        return final_state

    def get_graph_image(self, output_path: str = "pet_care_workflow.png"):
        """
        生成工作流图的可视化图像

        Args:
            output_path: 输出图像文件路径

        Returns:
            bytes: PNG格式的图像数据
        """
        try:
            graph_image = self.graph.get_graph().draw_mermaid_png()

            # 保存图像
            with open(output_path, "wb") as f:
                f.write(graph_image)

            return graph_image
        except Exception as e:
            print(f"生成工作流图失败: {e}")
            return None


# 导出全局图实例
graph = PetCareAgent().graph

__all__ = [
    "PetCareAgent",
    "graph"
]
