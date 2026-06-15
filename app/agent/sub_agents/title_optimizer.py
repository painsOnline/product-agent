"""
文件名称：title_optimizer.py
作者：shop-tool
时间：2026-06-15
逻辑说明：Title Optimizer 子 Agent，create_agent + middleware + state_schema.
"""
from typing import Any

from langchain.agents import create_agent

from app.prompts import get_title_optimizer_prompt
from app.agent.sub_agents.base import BaseSubAgent
from app.entities.agent_state import AgentState


class TitleOptimizer(BaseSubAgent):
    """标题优化子 Agent."""

    def create_agent(self, llm: Any, middleware: tuple = ()) -> Any:
        return create_agent(
            model=llm,
            tools=[],
            system_prompt=get_title_optimizer_prompt(),
            middleware=middleware,
            state_schema=AgentState,
            name="title_optimizer",
        )


title_optimizer = TitleOptimizer()
