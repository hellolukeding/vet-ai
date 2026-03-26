"""Runtime readiness checks used by diagnostics and deployment workflows."""

from importlib.util import find_spec
from typing import Dict

from core.llm_factory import resolve_llm_config

CRITICAL_DEPENDENCIES = ("bs4", "lxml")


def get_dependency_status() -> Dict[str, Dict[str, bool]]:
    """Check whether critical runtime dependencies are importable."""
    return {
        name: {"installed": find_spec(name) is not None}
        for name in CRITICAL_DEPENDENCIES
    }


def get_readiness_status() -> Dict[str, object]:
    """Aggregate runtime readiness from config and critical dependencies."""
    llm = resolve_llm_config()
    dependencies = get_dependency_status()

    dependency_issues = [
        f"{name} 未安装"
        for name, info in dependencies.items()
        if not info.get("installed", False)
    ]
    dependency_ready = not dependency_issues

    issues = [*llm["issues"], *dependency_issues]
    return {
        "ready": llm["ready"] and dependency_ready,
        "checks": {
            "llm": {
                "ready": llm["ready"],
                "model_name": llm["model_name"],
                "base_url": llm["base_url"],
                "api_key_masked": llm["api_key_masked"],
                "issues": llm["issues"],
            },
            "dependencies": {
                "ready": dependency_ready,
                "details": dependencies,
                "issues": dependency_issues,
            },
        },
        "issues": issues,
    }
