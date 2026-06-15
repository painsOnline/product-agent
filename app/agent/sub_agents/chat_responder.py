"""
文件名称：chat_responder.py
作者：shop-tool
时间：2026-06-16
逻辑说明：聊天响应子 Agent，仅回答商品相关提问，超出范围则拒绝.
"""
from typing import Any

from langchain.agents import create_agent

from app.prompts import get_prompt
from app.agent.sub_agents.base import BaseSubAgent
from app.entities.agent_state import AgentState


class ChatResponder(BaseSubAgent):
    """聊天响应子 Agent."""

    def create_agent(self, llm: Any, middleware: tuple = ()) -> Any:
        return create_agent(
            model=llm,
            tools=[],
            system_prompt=get_prompt("chat_responder_prompt", ""),
            middleware=middleware,
            state_schema=AgentState,
            name="chat_responder",
        )


chat_responder = ChatResponder()
