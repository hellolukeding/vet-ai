import asyncio
import json

from backend.element.ele_diagnosis import CreateDiagnosisRequest
from backend.routers import diagnosis as herb_router
from backend.routers import diagnosis_graph as western_router
from core.diagnosis_assessment import (
    DiagnosisAssessment,
    EmergencyAssessment,
    RecommendedTest,
    RecommendedTests,
    TemporaryCare,
    generate_assessment,
    pending_assessment,
)
from core.herb_result import format_herb_result
from core.tasks.task_executor import TaskExecutor
from core.tasks.task_manager import TaskQueueManager

ASSESSMENT = DiagnosisAssessment(
    emergency=EmergencyAssessment(
        level="urgent",
        reasons=["持续呕吐"],
        action="尽快就医",
        missing_information=["无"],
    ),
    recommended_tests=RecommendedTests(
        items=[
            RecommendedTest(
                name="血常规",
                purpose="评估感染和脱水",
                priority="recommended",
                related_findings=["持续呕吐"],
                condition="无附加条件",
            )
        ]
    ),
    temporary_care=TemporaryCare(
        actions=["保持安静"],
        avoid=["不要自行喂药"],
        escalation_signs=["意识异常"],
    ),
    warnings=["本评估仅供辅助，不能替代执业兽医诊断"],
).model_dump()
GENERATED_ASSESSMENT = {
    "emergency": {
        key: value for key, value in ASSESSMENT["emergency"].items() if key != "status"
    },
    "recommended_tests": {"items": ASSESSMENT["recommended_tests"]["items"]},
    "temporary_care": {
        key: value
        for key, value in ASSESSMENT["temporary_care"].items()
        if key != "status"
    },
    "warnings": ASSESSMENT["warnings"],
}


def response_json(response):
    return json.loads(response.body)


def test_western_sync_response_only_adds_assessment(monkeypatch):
    old_data = {
        "description": "持续呕吐",
        "diagnosis": [{"symptom": "胃肠炎", "reason": "呕吐", "probability": 0.6}],
        "medications": [],
    }

    async def fake_assessment(_description):
        return ASSESSMENT

    async def fake_graph(_state):
        return old_data

    monkeypatch.setattr(western_router, "generate_assessment", fake_assessment)
    monkeypatch.setattr(western_router.graph, "ainvoke", fake_graph)

    body = response_json(
        asyncio.run(
            western_router.diagnose(
                western_router.DiagnosisRequest(description="持续呕吐"),
                async_mode=False,
            )
        )
    )

    assert body["data"] == old_data
    assert body["assessment"] == ASSESSMENT
    assert set(body) == {"message", "disclaimer", "data", "code", "assessment"}


def test_herb_sync_keeps_data_as_list(monkeypatch):
    async def fake_assessment(_description):
        return ASSESSMENT

    async def fake_graph(_state):
        return {"zhengming": [], "prescriptions": [], "nursing": []}

    monkeypatch.setattr(herb_router, "generate_assessment", fake_assessment)
    monkeypatch.setattr(herb_router.herb_graph, "ainvoke", fake_graph)

    body = response_json(
        asyncio.run(
            herb_router.create_herb_diagnosis(
                CreateDiagnosisRequest(description="食欲下降"), async_mode=False
            )
        )
    )

    assert body["data"] == []
    assert body["assessment"] == ASSESSMENT


def test_pending_assessment_has_stable_shape():
    assessment = pending_assessment()

    assert assessment["status"] == "pending"
    assert assessment["emergency"]["level"] == "unknown"
    assert assessment["recommended_tests"]["items"]
    assert assessment["temporary_care"]["actions"]


def test_all_assessment_states_have_no_empty_fields():
    def assert_populated(value):
        if isinstance(value, dict):
            assert value
            for nested in value.values():
                assert_populated(nested)
        elif isinstance(value, list):
            assert value
            for nested in value:
                assert_populated(nested)
        elif isinstance(value, str):
            assert value.strip()
        else:
            assert value is not None

    assert_populated(ASSESSMENT)
    assert_populated(pending_assessment())
    from core.diagnosis_assessment import unavailable_assessment

    assert_populated(unavailable_assessment())


class FakeRedis:
    def __init__(self):
        self.values = {}

    def setex(self, key, _ttl, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)


def test_async_assessment_is_stored_outside_original_result():
    redis = FakeRedis()
    manager = TaskQueueManager(redis_client=redis)
    redis.values["task_result:task-1"] = json.dumps({"diagnoses": ["原结果"]})

    assert manager.set_task_assessment("task-1", ASSESSMENT) is True

    assert manager.get_task_result("task-1") == {"diagnoses": ["原结果"]}
    assert manager.get_task_assessment("task-1") == ASSESSMENT


def test_western_async_executor_uses_graph_and_preserves_result_shape(monkeypatch):
    class Manager:
        def __init__(self):
            self.assessment = None

        def update_task_progress(self, *_args):
            pass

        def set_task_assessment(self, _task_id, assessment):
            self.assessment = assessment

    class Graph:
        async def ainvoke(self, state):
            return {
                "description": state["description"],
                "diagnosis": [{"symptom": "胃肠炎"}],
                "medications": [],
            }

    async def fake_assessment(_description):
        return ASSESSMENT

    manager = Manager()
    executor = TaskExecutor(manager)
    monkeypatch.setattr("core.tasks.task_executor.generate_assessment", fake_assessment)
    monkeypatch.setattr(
        executor,
        "_get_graph_diagnosis_agent",
        lambda: type("Agent", (), {"graph": Graph()})(),
    )

    result = asyncio.run(
        executor.execute_graph_diagnosis("task-1", {"query": "持续呕吐"})
    )

    assert result == {
        "description": "持续呕吐",
        "diagnosis": [{"symptom": "胃肠炎"}],
        "medications": [],
    }
    assert manager.assessment == ASSESSMENT


def test_assessment_failure_isolated_from_diagnosis(monkeypatch):
    def failed_llm(**_kwargs):
        raise RuntimeError("model unavailable: {bad response}")

    monkeypatch.setattr("core.diagnosis_assessment.create_chat_llm", failed_llm)

    result = asyncio.run(generate_assessment("持续呕吐"))

    assert result["status"] == "unavailable"
    assert result["emergency"]["level"] == "unknown"


def test_assessment_json_output_is_validated(monkeypatch):
    class RawResult:
        content = json.dumps(GENERATED_ASSESSMENT, ensure_ascii=False)

    class FakeLLM:
        async def ainvoke(self, _messages):
            return RawResult()

    monkeypatch.setattr(
        "core.diagnosis_assessment.create_chat_llm", lambda **_kwargs: FakeLLM()
    )

    result = asyncio.run(generate_assessment("持续呕吐"))

    assert result == ASSESSMENT


def test_assessment_extracts_json_from_markdown(monkeypatch):
    class RawResult:
        content = (
            f"```json\n{json.dumps(GENERATED_ASSESSMENT, ensure_ascii=False)}\n```"
        )

    class FakeLLM:
        async def ainvoke(self, _messages):
            return RawResult()

    monkeypatch.setattr(
        "core.diagnosis_assessment.create_chat_llm", lambda **_kwargs: FakeLLM()
    )

    assert asyncio.run(generate_assessment("持续呕吐")) == ASSESSMENT


def test_assessment_rejects_empty_model_output(monkeypatch):
    class RawResult:
        content = "{}"

    class FakeLLM:
        async def ainvoke(self, _messages):
            return RawResult()

    monkeypatch.setattr(
        "core.diagnosis_assessment.create_chat_llm", lambda **_kwargs: FakeLLM()
    )

    assert asyncio.run(generate_assessment("持续呕吐"))["status"] == "unavailable"


def test_western_sync_starts_assessment_and_graph_concurrently(monkeypatch):
    graph_started = asyncio.Event()
    assessment_started = asyncio.Event()

    async def fake_graph(_state):
        graph_started.set()
        await assessment_started.wait()
        return {"description": "咳嗽", "diagnosis": [], "medications": []}

    async def fake_assessment(_description):
        assessment_started.set()
        await graph_started.wait()
        return ASSESSMENT

    monkeypatch.setattr(western_router.graph, "ainvoke", fake_graph)
    monkeypatch.setattr(western_router, "generate_assessment", fake_assessment)

    response = asyncio.run(
        western_router.diagnose(
            western_router.DiagnosisRequest(description="咳嗽"), async_mode=False
        )
    )
    assert response_json(response)["assessment"] == ASSESSMENT


def test_herb_formatter_preserves_existing_item_fields():
    result = format_herb_result(
        {
            "zhengming": [
                {
                    "zhengming": "脾胃虚弱",
                    "description": "食欲下降",
                    "probability": 0.6,
                    "therapy": "健脾益气",
                }
            ],
            "prescriptions": [
                {
                    "zhengming": "脾胃虚弱",
                    "prescription_type": "基础方",
                    "prescription_name": "示例方",
                    "composition": "由中兽医确定",
                    "usage": "由中兽医面诊后开具",
                }
            ],
            "nursing": [],
        }
    )

    assert set(result[0]) == {
        "zhengming",
        "description",
        "p",
        "therapy",
        "base",
        "continue",
        "suggest",
        "base_prescription",
        "base_prescription_usage",
        "continue_prescription",
        "continue_prescription_usage",
        "suggest_prescription",
        "suggest_prescription_usage",
    }
    assert result[0]["base_prescription"] == "示例方"


def test_herb_async_executor_uses_same_graph_and_keeps_result_shape(monkeypatch):
    class Manager:
        assessment = None

        def update_task_progress(self, *_args):
            pass

        def set_task_assessment(self, _task_id, assessment):
            self.assessment = assessment

    async def fake_graph(state):
        return {
            "description": state["description"],
            "zhengming": [],
            "prescriptions": [],
            "nursing": [],
        }

    async def fake_assessment(_description):
        return ASSESSMENT

    manager = Manager()
    executor = TaskExecutor(manager)
    monkeypatch.setattr("core.tasks.task_executor.generate_assessment", fake_assessment)
    monkeypatch.setattr("core.tasks.task_executor.herb_graph.ainvoke", fake_graph)

    result = asyncio.run(
        executor.execute_herb_diagnosis("task-1", {"symptoms": "食欲下降"})
    )
    assert result == {"diagnoses": [], "symptoms": "食欲下降"}
    assert manager.assessment == ASSESSMENT
