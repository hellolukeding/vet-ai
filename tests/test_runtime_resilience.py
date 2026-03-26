import asyncio
import json

import pytest
from bs4 import BeautifulSoup as RealBeautifulSoup
from bs4 import FeatureNotFound

from backend.runtime_checks import get_readiness_status
from core.langgraph.nodes.literature_search_node import LiteratureSearchNode
from core.langgraph.tools import web_search
from core.llm_factory import LLMConfigurationError, create_chat_llm, resolve_llm_config


def test_build_soup_falls_back_to_html_parser(monkeypatch):
    html = "<html><body><p>fallback-ok</p></body></html>"
    parsers = []

    def fake_beautiful_soup(markup, parser):
        parsers.append(parser)
        if parser == "lxml":
            raise FeatureNotFound("lxml unavailable")
        return RealBeautifulSoup(markup, parser)

    monkeypatch.setattr(web_search, "BeautifulSoup", fake_beautiful_soup)

    soup = web_search.build_soup(html)

    assert soup.p.get_text() == "fallback-ok"
    assert parsers == ["lxml", "html.parser"]


def test_literature_search_skips_error_placeholder_results(monkeypatch):
    error_payload = json.dumps(
        [
            {
                "id": "error_123",
                "title": "搜索请求错误",
                "link": "https://www.baidu.com/s?wd=test",
                "snippet": "搜索请求失败: parser missing",
            }
        ],
        ensure_ascii=False,
    )

    class SearchToolStub:
        @staticmethod
        def invoke(_payload):
            return error_payload

    class FetchToolStub:
        @staticmethod
        def invoke(_result_id):
            raise AssertionError("error placeholder should not trigger fetch")

    monkeypatch.setattr(
        "core.langgraph.nodes.literature_search_node.web_search_tool", SearchToolStub
    )
    monkeypatch.setattr(
        "core.langgraph.nodes.literature_search_node.fetch_webpage_tool", FetchToolStub
    )

    result = asyncio.run(LiteratureSearchNode({"description": "猫咪呕吐"}))

    assert result == {"literature": []}


def test_create_chat_llm_rejects_missing_api_key(monkeypatch):
    monkeypatch.setattr("core.llm_factory.settings.MODEL_NAME", "test-model")
    monkeypatch.setattr("core.llm_factory.settings.BASE_URL", "https://example.com/v1")
    monkeypatch.setattr("core.llm_factory.settings.API_KEY", "")

    config = resolve_llm_config()

    assert config["ready"] is False
    assert "API_KEY" in " ".join(config["issues"])

    with pytest.raises(LLMConfigurationError):
        create_chat_llm()


def test_readiness_status_reports_missing_llm_config(monkeypatch):
    monkeypatch.setattr(
        "backend.runtime_checks.resolve_llm_config",
        lambda: {
            "ready": False,
            "issues": ["API_KEY 未配置"],
            "model_name": "test-model",
            "base_url": "https://example.com/v1",
            "api_key_masked": "",
        },
    )
    monkeypatch.setattr(
        "backend.runtime_checks.get_dependency_status",
        lambda: {"lxml": {"installed": True}, "bs4": {"installed": True}},
    )

    status = get_readiness_status()

    assert status["ready"] is False
    assert status["checks"]["llm"]["ready"] is False
    assert status["checks"]["dependencies"]["ready"] is True
