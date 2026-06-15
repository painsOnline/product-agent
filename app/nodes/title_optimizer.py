"""
文件名称：title_optimizer.py
作者：shop-tool
时间：2026-06-15
逻辑说明：标题优化节点 — 构造任务 prompt，调用子 Agent，JSON 提取，最多重试 3 次.
"""
import json as _json
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from app.entities.agent_state import AgentState

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _build_task_message(state: AgentState) -> HumanMessage:
    """从 state 构造标题优化任务 prompt."""
    original_title = state.get("original_title", "")
    user_content = state.get("user_content", "按标准规则优化")
    ban_words = state.get("ban_words", [])
    title_max_len = state.get("title_max_len", 45)
    parts = [f"原始标题: {original_title}", f"用户要求: {user_content}"]
    if ban_words:
        parts.append(f"禁用词: {ban_words}")
    parts.append(f"最大长度: {title_max_len}字符")
    parts.append("请输出 json 格式结果。")
    return HumanMessage(content="\n".join(parts))


def _extract_json(messages: list[Any], required_key: str) -> dict | None:
    """从消息列表中提取最后一个包含 required_key 的 JSON 对象."""
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
    """标题优化节点：构造任务 prompt，调用子 Agent，提取 JSON 结果，最多重试 3 次."""
    sub_agents = sub_agents or {}
    agent = sub_agents.get("title_optimizer")
    if agent is None:
        return {"_title_done": True}

    task_input = {
        **state,
        "messages": list(state.get("messages", [])) + [_build_task_message(state)],
    }

    try:
        result = await agent.ainvoke(task_input, config)
    except Exception as e:
        retries = state.get("_title_retries", 0) + 1
        logger.warning("title_optimizer LLM failed (retry %d/%d): %s", retries, MAX_RETRIES, e)
        if retries < MAX_RETRIES:
            return {"_title_retries": retries}
        return {"_title_done": True, "error_info": {"title_failed": str(e)}}

    msgs = result.get("messages", [])
    title_output = _extract_json(msgs, "new_title")

    if title_output:
        current = state.get("latest_result") or {}
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
            "messages": result.get("messages", state.get("messages", [])),
        }

    retries = state.get("_title_retries", 0) + 1
    logger.warning("title_optimizer JSON parse failed (retry %d/%d)", retries, MAX_RETRIES)
    if retries < MAX_RETRIES:
        return {"_title_retries": retries}
    return {"_title_done": True, "error_info": {"title_parse_failed": "JSON parse failed after retries"}}
