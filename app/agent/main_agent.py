"""
文件名称：main_agent.py
作者：shop-tool
时间：2026-06-14
逻辑说明：基于 DeepAgents 原生库构建 Supervisor Agent.

Redis 客户端和 DB 会话从 RequestContext 注入，不在模块内创建连接（DIP）.
"""
import logging
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.middleware.summarization import SummarizationMiddleware

from app.agent.checkpointer import build_checkpointer
from app.agent.llm import create_llm
from app.agent.prompts import get_supervisor_prompt
from app.agent.sub_agent_builder import SubAgentBuilder
from app.entities.agent import SupervisorOutput

logger = logging.getLogger(__name__)

_AGENT_CACHE: dict[str, Any] = {}


def build_supervisor_agent(
    llm_config: dict[str, Any] | None = None,
    callbacks: list | None = None,
    redis_client: Any = None,
):
    """构建 Supervisor DeepAgent.

    Args:
        llm_config: LLM 配置字典
        callbacks: LangChain 回调列表
        redis_client: Redis 客户端，从 RequestContext 注入
    """
    llm = create_llm(llm_config)
    checkpointer = build_checkpointer(redis_client)
    builder = SubAgentBuilder(llm_config)

    summarization = SummarizationMiddleware(
        model=llm,
        trigger=("fraction", 0.5),
        keep=("fraction", 0.1),
        backend=StateBackend(),
    )

    agent = create_deep_agent(
        name="supervisor",
        model=llm,
        system_prompt=get_supervisor_prompt(),
        subagents=builder.build_all(),
        middleware=[summarization],
        checkpointer=checkpointer,
        backend=StateBackend(),
        response_format=SupervisorOutput,
        interrupt_on={"confirm": True},
        callbacks=callbacks or [],
    )

    logger.info("Supervisor DeepAgent built")
    return agent


def get_agent(
    thread_id: str,
    llm_config: dict[str, Any] | None = None,
    callbacks: list | None = None,
    redis_client: Any = None,
):
    """获取或创建 Agent 实例（WebSocket 生命周期缓存）."""
    if thread_id not in _AGENT_CACHE:
        _AGENT_CACHE[thread_id] = build_supervisor_agent(
            llm_config, callbacks, redis_client
        )
    return _AGENT_CACHE[thread_id]


def remove_agent(thread_id: str) -> None:
    """移除 Agent 实例."""
    _AGENT_CACHE.pop(thread_id, None)
