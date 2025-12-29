import os

from langchain_core.messages import (AIMessage, HumanMessage, SystemMessage,
                                     ToolMessage)
from langchain_openai import ChatOpenAI

from backend.settings import settings
from core.langgraph.state import VetAgentState


def get_llm():
    """创建并返回配置好的ChatOpenAI实例"""
    model_name = settings.MODEL_NAME or "deepseek-ai/DeepSeek-V3"
    base_url = settings.BASE_URL or "https://api-inference.modelscope.cn/v1"
    api_key = settings.API_KEY or ""
    temperature = 0.6

    return ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
    )


async def call_model(state: VetAgentState) -> VetAgentState:

    # 确保我们有消息且最后一条消息是正确的类型
    if state['messages']:
        last_message = state['messages'][-1]
        if not isinstance(last_message, (AIMessage, SystemMessage, HumanMessage, ToolMessage)):
            last_message = HumanMessage(content=last_message.content)
            state['messages'][-1] = last_message

    # 提取 messages 中最后一个 HumanMessage（从后向前查找）
    messages = state.get("messages", [])
    last_human = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human = msg
            break

    # 按 LangGraph 期望：不要仅就地修改传入的 state，而是返回一个 partial state（dict）
    if last_human is not None:
        # 把最后一条 human 消息文本放到现有的 `description` 字段，保证在 State schema 中可见
        return {"description": last_human.content}

    # 如果没有 human 消息，返回空字典（表示无更新）
    return {}
