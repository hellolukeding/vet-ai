"""
任务执行器

负责执行不同类型的AI任务，调用相应的Agent并处理结果。
"""

from typing import Any, Callable, Dict

from config.logger import logger
from core.ai_diagnosis.diagnosis import Diagnosis
from core.ai_diagnosis.herb_diagnosis import HerbDiagnosis
from core.langgraph.agent import VetAgent
from core.plan.agent import PetCareAgent
from core.tasks.task_manager import TaskQueueManager


class TaskExecutor:
    """
    任务执行器

    执行各种类型的AI任务，支持进度回调。
    """

    def __init__(self, task_manager: TaskQueueManager):
        """
        初始化任务执行器

        Args:
            task_manager: 任务队列管理器实例
        """
        self.task_manager = task_manager

        # 延迟初始化Agent实例
        self._diagnosis_agent = None
        self._herb_diagnosis_agent = None
        self._graph_diagnosis_agent = None
        self._pet_care_agent = None

    def _get_diagnosis_agent(self) -> Diagnosis:
        """获取西医诊断Agent实例"""
        if self._diagnosis_agent is None:
            self._diagnosis_agent = Diagnosis()
        return self._diagnosis_agent

    def _get_herb_diagnosis_agent(self) -> HerbDiagnosis:
        """获取中医诊断Agent实例"""
        if self._herb_diagnosis_agent is None:
            self._herb_diagnosis_agent = HerbDiagnosis()
        return self._herb_diagnosis_agent

    def _get_graph_diagnosis_agent(self) -> VetAgent:
        """获取LangGraph诊断Agent实例"""
        if self._graph_diagnosis_agent is None:
            self._graph_diagnosis_agent = VetAgent()
        return self._graph_diagnosis_agent

    def _get_pet_care_agent(self) -> PetCareAgent:
        """获取宠物护理计划Agent实例"""
        if self._pet_care_agent is None:
            self._pet_care_agent = PetCareAgent()
        return self._pet_care_agent

    async def execute_diagnosis(
        self,
        task_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行西医诊断任务

        Args:
            task_id: 任务ID
            task_data: 任务数据，包含 symptoms 字段

        Returns:
            Dict: 诊断结果
        """
        try:
            symptoms = task_data.get("symptoms", "")
            logger.info(f"开始西医诊断任务: {task_id}, 症状: {symptoms[:50]}...")

            # 更新进度
            self.task_manager.update_task_progress(
                task_id, "分析症状", 20, "正在分析症状描述"
            )

            # 调用诊断Agent
            agent = self._get_diagnosis_agent()
            result = agent.diagnosis(symptoms)

            # 更新进度
            self.task_manager.update_task_progress(
                task_id, "生成结果", 80, "正在生成诊断结果"
            )

            logger.info(f"西医诊断任务完成: {task_id}, 结果数量: {len(result)}")

            return {
                "diagnoses": result,
                "symptoms": symptoms
            }

        except Exception as e:
            logger.error(f"西医诊断任务执行失败: {task_id}, 错误: {e}")
            raise

    async def execute_herb_diagnosis(
        self,
        task_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行中医诊断任务

        Args:
            task_id: 任务ID
            task_data: 任务数据，包含 symptoms 字段

        Returns:
            Dict: 中医诊断结果
        """
        try:
            symptoms = task_data.get("symptoms", "")
            logger.info(f"开始中医诊断任务: {task_id}, 症状: {symptoms[:50]}...")

            # 更新进度
            self.task_manager.update_task_progress(
                task_id, "辨证分析", 20, "正在进行中医辨证分析"
            )

            # 调用中医诊断Agent
            agent = self._get_herb_diagnosis_agent()
            result = agent.diagnosis(symptoms)

            # 更新进度
            self.task_manager.update_task_progress(
                task_id, "生成方剂", 80, "正在生成处方建议"
            )

            logger.info(f"中医诊断任务完成: {task_id}, 结果数量: {len(result)}")

            return {
                "diagnoses": result,
                "symptoms": symptoms
            }

        except Exception as e:
            logger.error(f"中医诊断任务执行失败: {task_id}, 错误: {e}")
            raise

    async def execute_graph_diagnosis(
        self,
        task_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行LangGraph智能诊断任务

        Args:
            task_id: 任务ID
            task_data: 任务数据，包含 query 字段

        Returns:
            Dict: 智能诊断结果
        """
        try:
            query = task_data.get("query", "")
            logger.info(f"开始智能诊断任务: {task_id}, 查询: {query[:50]}...")

            # 更新进度
            self.task_manager.update_task_progress(
                task_id, "初步诊断", 20, "正在进行初步病情诊断"
            )

            # 调用LangGraph诊断Agent
            agent = self._get_graph_diagnosis_agent()

            # 创建进度回调
            def progress_callback(stage: str, progress: int):
                self.task_manager.update_task_progress(
                    task_id, stage, progress, f"正在{stage}"
                )

            result = await agent.run(query, progress_callback=progress_callback)

            # 更新进度
            self.task_manager.update_task_progress(
                task_id, "生成报告", 90, "正在生成结构化报告"
            )

            logger.info(f"智能诊断任务完成: {task_id}")

            return result

        except Exception as e:
            logger.error(f"智能诊断任务执行失败: {task_id}, 错误: {e}")
            raise

    async def execute_pet_care_plan(
        self,
        task_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行宠物护理计划任务

        Args:
            task_id: 任务ID
            task_data: 任务数据，包含 user_query 和可选的宠物信息字段

        Returns:
            Dict: 护理计划结果
        """
        try:
            user_query = task_data.get("user_query", "")

            # 转换字段名：pet_name -> name, pet_species -> species, etc.
            pet_info = {}
            field_mapping = {
                "pet_name": "name",
                "pet_species": "species",
                "pet_breed": "breed",
                "pet_age": "age",
                "pet_weight": "weight",
                "pet_sex": "sex",
                "pet_neutered": "neutered"
            }

            for task_field, agent_field in field_mapping.items():
                value = task_data.get(task_field)
                if value is not None:
                    # 转换 weight 和 neutered 为字符串格式
                    if task_field == "pet_weight":
                        pet_info[agent_field] = str(value)
                    elif task_field == "pet_neutered":
                        pet_info[agent_field] = "true" if value else "false"
                    else:
                        pet_info[agent_field] = value

            logger.info(
                f"开始宠物护理计划任务: {task_id}, "
                f"查询: {user_query[:50]}..."
            )

            # 更新进度
            self.task_manager.update_task_progress(
                task_id, "提取宠物信息", 10, "正在提取和补全宠物信息"
            )

            # 调用宠物护理计划Agent
            agent = self._get_pet_care_agent()

            # 创建进度回调
            def progress_callback(stage: str, progress: int):
                self.task_manager.update_task_progress(
                    task_id, stage, progress, f"正在{stage}"
                )

            result = await agent.run(
                user_query=user_query,
                pet_info=pet_info if pet_info else None,
                progress_callback=progress_callback
            )

            # 更新进度
            self.task_manager.update_task_progress(
                task_id, "完成", 100, "护理计划生成完成"
            )

            logger.info(f"宠物护理计划任务完成: {task_id}")

            return result

        except Exception as e:
            logger.error(f"宠物护理计划任务执行失败: {task_id}, 错误: {e}")
            raise

    async def execute_task(
        self,
        task_type: str,
        task_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行任务（统一入口）

        Args:
            task_type: 任务类型
            task_id: 任务ID
            task_data: 任务数据

        Returns:
            Dict: 任务执行结果

        Raises:
            ValueError: 不支持的任务类型
        """
        from core.tasks.task_types import TaskType

        # 设置任务为处理中状态
        self.task_manager.set_task_processing(task_id)

        # 根据任务类型调用对应的执行方法
        if task_type == TaskType.DIAGNOSIS:
            return await self.execute_diagnosis(task_id, task_data)
        elif task_type == TaskType.HERB_DIAGNOSIS:
            return await self.execute_herb_diagnosis(task_id, task_data)
        elif task_type == TaskType.GRAPH_DIAGNOSIS:
            return await self.execute_graph_diagnosis(task_id, task_data)
        elif task_type == TaskType.PET_CARE_PLAN:
            return await self.execute_pet_care_plan(task_id, task_data)
        else:
            raise ValueError(f"不支持的任务类型: {task_type}")
