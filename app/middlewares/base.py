"""
文件名称：base.py
作者：shop-tool
时间：2026-06-15
逻辑说明：中间件基类，子 Agent 通过 create_agent(middleware=[...]) 使用.

同时继承 AgentMiddleware（子 Agent 生命周期）和 BaseCallbackHandler（LLM 日志）.
"""
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.callbacks.base import BaseCallbackHandler


class BaseMiddleware(AgentMiddleware, BaseCallbackHandler):
    """中间件基类.

    子类按需实现:
        async abefore_agent(state, runtime) → dict | None
        async aafter_agent(state, runtime) → dict | None
        async aafter_model(state, runtime) → dict | None
        on_llm_start / on_llm_end / on_llm_error
    """

    enabled: bool = True
