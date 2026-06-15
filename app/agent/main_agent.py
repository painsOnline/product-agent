"""
文件名称：main_agent.py
作者：shop-tool
时间：2026-06-15
逻辑说明：Agent 构建入口，手动 StateGraph + create_agent 子 Agent.

- 子 Agent: create_agent(middleware=[...])
- 中间件: SummarizationMiddleware(官方压缩) + LoggingMiddleware(日志)
- 图: core/graph.py 手动 StateGraph
"""
import logging
from typing import Any

from langchain.agents.middleware.summarization import SummarizationMiddleware

from app.agent.sub_agent_builder import discover_sub_agents
from app.core.checkpointer import build_checkpointer
from app.core.graph import build_graph
from app.core.llm import create_llm
from app.middlewares import discover_middlewares

logger = logging.getLogger(__name__)

_AGENT_CACHE: dict[str, Any] = {}


def build_supervisor_agent(
    llm_config: dict[str, Any] | None = None,
    redis_client: Any = None,
) -> Any:
    """构建 Supervisor Graph.

    子 Agent 注入官方 SummarizationMiddleware（50% 窗口触发，保留 10 条）
    + LoggingMiddleware（t_agent_action_logs 记录）.
    """
    llm = create_llm(llm_config or {})
    checkpointer = build_checkpointer(redis_client)

    summarization = SummarizationMiddleware(
        model=llm,
        trigger=("fraction", 0.5),
        keep=("messages", 10),
    )
    custom_middleware = discover_middlewares()
    middleware = (summarization, *custom_middleware)

    sub_agents = discover_sub_agents(llm, middleware=middleware)
    logger.info("发现 %d 个子 Agent: %s", len(sub_agents), list(sub_agents.keys()))

    graph = build_graph(sub_agents, checkpointer=checkpointer)
    logger.info("StateGraph 构建完成")
    return graph


def get_agent(
    thread_id: str,
    llm_config: dict[str, Any] | None = None,
    redis_client: Any = None,
) -> Any:
    if thread_id not in _AGENT_CACHE:
        _AGENT_CACHE[thread_id] = build_supervisor_agent(llm_config, redis_client)
    return _AGENT_CACHE[thread_id]


def remove_agent(thread_id: str) -> None:
    _AGENT_CACHE.pop(thread_id, None)
