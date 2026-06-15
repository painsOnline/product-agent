"""
文件名称：attribute_matcher.py
作者：shop-tool
时间：2026-06-15
逻辑说明：属性匹配节点 — 构造任务 prompt，调用子 Agent，JSON 提取，最多重试 3 次.
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
    """从 state 构造属性匹配任务 prompt."""
    original_attrs = state.get("original_attrs", [])
    target_attrs = state.get("target_attrs", [])
    parts = []
    if original_attrs:
        parts.append(f"源属性: {_json.dumps(original_attrs, ensure_ascii=False)}")
    if target_attrs:
        parts.append(f"目标属性: {_json.dumps(target_attrs, ensure_ascii=False)}")
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


async def attribute_matcher_node(
    state: AgentState, config: RunnableConfig, *, sub_agents: dict[str, Any] | None = None
) -> dict[str, Any]:
    """属性匹配节点：构造任务 prompt，调用子 Agent，提取 JSON 结果，最多重试 3 次."""
    sub_agents = sub_agents or {}
    agent = sub_agents.get("attribute_matcher")
    if agent is None:
        return {"_attr_done": True}

    task_input = {
        **state,
        "messages": list(state.get("messages", [])) + [_build_task_message(state)],
    }

    try:
        result = await agent.ainvoke(task_input, config)
    except Exception as e:
        retries = state.get("_attr_retries", 0) + 1
        logger.warning("attribute_matcher LLM failed (retry %d/%d): %s", retries, MAX_RETRIES, e)
        if retries < MAX_RETRIES:
            return {"_attr_retries": retries}
        return {"_attr_done": True, "error_info": {"attr_failed": str(e)}}

    msgs = result.get("messages", [])
    attr_output = _extract_json(msgs, "attr_mapping")

    if attr_output:
        current = state.get("latest_result") or {}
        return {
            "_attr_done": True,
            "latest_result": {
                **current,
                "attr_mapping": attr_output.get("attr_mapping", current.get("attr_mapping", [])),
                "warning": attr_output.get("warning", current.get("warning", {"has_warn": False, "warn_content": ""})),
                "suggestion": attr_output.get("suggestion", current.get("suggestion", {"summary": "", "items": []})),
            },
            "messages": result.get("messages", state.get("messages", [])),
        }

    retries = state.get("_attr_retries", 0) + 1
    logger.warning("attribute_matcher JSON parse failed (retry %d/%d)", retries, MAX_RETRIES)
    if retries < MAX_RETRIES:
        return {"_attr_retries": retries}
    return {"_attr_done": True, "error_info": {"attr_parse_failed": "JSON parse failed after retries"}}
