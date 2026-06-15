"""
文件名称：agent_state.py
作者：shop-tool
时间：2026-06-15
逻辑说明：Agent 全局 State TypedDict，create_supervisor / create_agent 共用.
"""
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """会话级全局 State.

    同时兼容 langchain.agents.AgentState（jump_to, structured_response），
    和项目业务字段（original_title, latest_result 等）。
    """

    # -- LangChain AgentState 必须字段 --
    messages: Annotated[list[BaseMessage], add_messages]
    jump_to: str | None
    structured_response: Any

    # -- 只读业务字段 --
    thread_id: str
    user_id: str
    import_product_id: str
    operate_type: str
    original_title: str
    original_attrs: list[dict[str, Any]]
    target_attrs: list[dict[str, Any]]
    title_max_len: int
    ban_words: list[str]

    # -- 读写业务字段 --
    user_content: str
    manual_data: dict[str, Any] | None
    latest_result: dict[str, Any]
    current_step: str
    hitl_status: str
    error_info: dict[str, Any] | None
    remaining_steps: int

    # -- 内部路由/追踪字段 --
    _route: str
    _intent: str
    _title_done: bool
    _attr_done: bool
    _chat_done: bool
    _title_retries: int
    _attr_retries: int
