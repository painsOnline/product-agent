"""
文件名称：intent_detector.py
作者：shop-tool
时间：2026-06-15
逻辑说明：意图识别子 Agent，判断用户意图（title/attribute/both/chat）.
"""
from typing import Any

from langchain.agents import create_agent

from app.prompts import get_prompt
from app.agent.sub_agents.base import BaseSubAgent
from app.entities.agent_state import AgentState


class IntentDetector(BaseSubAgent):
    """意图识别子 Agent."""

    def create_agent(self, llm: Any, middleware: tuple = ()) -> Any:
        return create_agent(
            model=llm,
            tools=[],
            system_prompt=get_prompt("intent_prompt", ""),
            middleware=middleware,
            state_schema=AgentState,
            name="intent_detector",
        )


intent_detector = IntentDetector()
