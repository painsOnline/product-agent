"""
文件名称：sub_agent_builder.py
作者：shop-tool
时间：2026-06-14
逻辑说明：子 Agent 构建器，通过注册表发现子 Agent 并批量构建（OCP）.

职责：
- 读取 sub_agents/__init__.py 中的 _REGISTRY
- 遍历每个工厂函数，传入 llm_config，构建 SubAgent 列表
- 不 hardcode 任何具体子 Agent 名称或创建逻辑

新增 Agent 只需两步，无需修改本文件：
1. 新建 sub_agents/new_agent.py，实现 create_sub_agent(llm_config) -> SubAgent
2. 在 sub_agents/__init__.py 的 _REGISTRY 中追加一行 import
"""
from typing import Any

from deepagents.middleware.subagents import SubAgent

from app.agent.sub_agents import get_registry


class SubAgentBuilder:
    """通过注册表发现并批量构建所有子 Agent."""

    def __init__(
        self,
        llm_config: dict[str, Any] | None = None,
    ) -> None:
        self._llm_config = llm_config

    def build_all(self) -> list[SubAgent]:
        """遍历注册表，构建全部已注册的子 Agent."""
        sub_agents: list[SubAgent] = []
        for factory in get_registry():
            sub_agents.append(factory(self._llm_config))
        return sub_agents
