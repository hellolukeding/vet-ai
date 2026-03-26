"""Shared LLM factory helpers for runtime validation and sanitized logging."""

from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI

from backend.settings import settings
from config.logger import logger


class LLMConfigurationError(RuntimeError):
    """Raised when the runtime LLM configuration is not usable."""


def mask_secret(secret: Optional[str]) -> str:
    """Return a masked secret for logs and diagnostics."""
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}***{secret[-4:]}"


def resolve_llm_config() -> Dict[str, Any]:
    """Resolve LLM config from settings and report readiness."""
    model_name = (settings.MODEL_NAME or "deepseek-ai/DeepSeek-V3").strip()
    base_url = (
        settings.BASE_URL or "https://api-inference.modelscope.cn/v1"
    ).strip()
    api_key = (settings.API_KEY or "").strip()

    issues = []
    if not model_name:
        issues.append("MODEL_NAME 未配置")
    if not base_url:
        issues.append("BASE_URL 未配置")
    if not api_key:
        issues.append("API_KEY 未配置")

    return {
        "model_name": model_name,
        "base_url": base_url,
        "api_key": api_key,
        "api_key_masked": mask_secret(api_key),
        "issues": issues,
        "ready": not issues,
    }


def create_chat_llm(*, temperature: float = 0.6) -> ChatOpenAI:
    """Create a configured ChatOpenAI instance or raise a config error."""
    config = resolve_llm_config()
    if not config["ready"]:
        message = "；".join(config["issues"])
        logger.error(f"LLM配置不可用: {message}")
        raise LLMConfigurationError(message)

    logger.debug(
        "初始化LLM客户端: model={}, base_url={}, api_key={}, temperature={}",
        config["model_name"],
        config["base_url"],
        config["api_key_masked"],
        temperature,
    )
    return ChatOpenAI(
        model=config["model_name"],
        base_url=config["base_url"],
        api_key=config["api_key"],
        temperature=temperature,
    )
