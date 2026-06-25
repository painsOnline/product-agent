"""
文件名称：title_optimizer.py
作者：shop-tool
时间：2026-06-15
逻辑说明：标题优化节点.
"""
import json as _json
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from app.core.langfuse_client import (
    create_callback_handler, get_trace_id, inject_callback, langfuse_event, langfuse_span,
)
from app.entities.agent_state import AgentState

logger = logging.getLogger(__name__)
MAX_RETRIES = 3


def _build_task_message(state: AgentState) -> HumanMessage:
    parts = [f"原始标题: {state.get('original_title', '')}",
             f"用户要求: {state.get('user_content', '按标准规则优化')}"]
    if state.get("ban_words"):
        parts.append(f"禁用词: {state.get('ban_words')}")
    parts.append(f"最大长度: {state.get('title_max_len', 45)}字符")
    parts.append("请输出 json 格式结果。")
    return HumanMessage(content="\n".join(parts))


def _extract_json(messages: list[Any], required_key: str) -> dict | None:
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        if not isinstance(content, str) or required_key not in content:
            continue
        try:
            cleaned = content.strip()
            if cleaned.startswith("```"):
                idx = cleaned.find("\n")
                cleaned = cleaned[idx + 1:] if idx > 0 else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed = _json.loads(cleaned.strip())
            if isinstance(parsed, dict) and required_key in parsed:
                return parsed
        except Exception:
            pass
    return None


async def title_optimizer_node(
    state: AgentState, config: RunnableConfig, *, sub_agents: dict[str, Any] | None = None
) -> dict[str, Any]:
    sub_agents = sub_agents or {}
    agent = sub_agents.get("title_optimizer")
    if agent is None:
        return {"_title_done": True}

    trace_id = get_trace_id()
    retries_before = state.get("_title_retries", 0)
    task_msg = _build_task_message(state)

    with langfuse_span("title_optimizer", input_data={
        "original_title": state.get("original_title", ""),
        "user_content": state.get("user_content", ""),
        "retry_attempt": retries_before,
    }):
        task_input = {**state, "messages": list(state.get("messages", [])) + [task_msg]}
        handler = create_callback_handler()
        _config = inject_callback(config, handler)

        try:
            result = await agent.ainvoke(task_input, _config)
        except Exception as e:
            retries = retries_before + 1
            langfuse_event(trace_id, "llm_error", metadata={"node": "title_optimizer", "attempt": retries, "error": str(e)}, level="ERROR")
            if retries < MAX_RETRIES:
                return {"_title_retries": retries}
            return {"_title_done": True, "error_info": {"title_failed": str(e)}}

        msgs = result.get("messages", [])
        title_output = _extract_json(msgs, "new_title")

        if title_output:
            current = state.get("latest_result") or {}
            langfuse_event(trace_id, "title_success", metadata={
                "new_title": title_output.get("new_title", ""),
                "title_note": title_output.get("title_note", ""),
            })
            return {
                "_title_done": True,
                "latest_result": {
                    **current,
                    "new_title": title_output.get("new_title", current.get("new_title", "")),
                    "original_title": title_output.get("original_title", state.get("original_title", "")),
                    "title_note": title_output.get("title_note", ""),
                    "warning": title_output.get("warning", current.get("warning", {"has_warn": False, "warn_content": ""})),
                    "suggestion": title_output.get("suggestion", current.get("suggestion", {"summary": "", "items": []})),
                },
                "messages": msgs,
            }

        retries = retries_before + 1
        langfuse_event(trace_id, "parse_error", metadata={
            "node": "title_optimizer", "attempt": retries, "max_retries": MAX_RETRIES,
            "error": "JSON 解析失败：缺少 new_title 字段",
        })
        if retries < MAX_RETRIES:
            return {"_title_retries": retries}
        return {"_title_done": True, "error_info": {"title_parse_failed": "JSON parse failed"}}
