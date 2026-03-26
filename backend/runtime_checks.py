"""Runtime readiness checks used by diagnostics and deployment workflows."""

from importlib.util import find_spec
from typing import Dict

from core.llm_factory import resolve_llm_config

REQUIRED_DEPENDENCIES = ("bs4",)
OPTIONAL_DEPENDENCIES = ("lxml",)


def get_dependency_status() -> Dict[str, Dict[str, bool]]:
    """Check whether runtime dependencies are importable."""
    status: Dict[str, Dict[str, bool]] = {}

    for name in REQUIRED_DEPENDENCIES:
        status[name] = {"installed": find_spec(name) is not None, "required": True}

    for name in OPTIONAL_DEPENDENCIES:
        status[name] = {"installed": find_spec(name) is not None, "required": False}

    return status


def get_readiness_status() -> Dict[str, object]:
    """Aggregate runtime readiness from config and critical dependencies."""
    llm = resolve_llm_config()
    dependencies = get_dependency_status()

    dependency_issues = [
        f"{name} 未安装"
        for name, info in dependencies.items()
        if info.get("required", True) and not info.get("installed", False)
    ]
    dependency_warnings = [
        f"{name} 未安装，将使用降级路径"
        for name, info in dependencies.items()
        if not info.get("required", True) and not info.get("installed", False)
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
                "warnings": dependency_warnings,
            },
        },
        "issues": issues,
        "warnings": dependency_warnings,
    }
