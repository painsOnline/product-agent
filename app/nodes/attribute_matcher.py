"""
文件名称：attribute_matcher.py
作者：shop-tool
时间：2026-06-15
逻辑说明：属性匹配节点.
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
    parts = []
    if state.get("original_attrs"):
        parts.append(f"源属性: {_json.dumps(state['original_attrs'], ensure_ascii=False)}")
    if state.get("target_attrs"):
        parts.append(f"目标属性: {_json.dumps(state['target_attrs'], ensure_ascii=False)}")
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
            return _json.loads(cleaned.strip())
        except Exception:
            pass
    return None


async def attribute_matcher_node(
    state: AgentState, config: RunnableConfig, *, sub_agents: dict[str, Any] | None = None
) -> dict[str, Any]:
    sub_agents = sub_agents or {}
    agent = sub_agents.get("attribute_matcher")
    if agent is None:
        return {"_attr_done": True}

    trace_id = get_trace_id()
    retries_before = state.get("_attr_retries", 0)
    task_msg = _build_task_message(state)

    with langfuse_span("attribute_matcher", input_data={
        "original_attrs": state.get("original_attrs", []),
        "target_attrs": state.get("target_attrs", []),
        "retry_attempt": retries_before,
    }):
        task_input = {**state, "messages": list(state.get("messages", [])) + [task_msg]}
        handler = create_callback_handler()
        _config = inject_callback(config, handler)

        try:
            result = await agent.ainvoke(task_input, _config)
        except Exception as e:
            retries = retries_before + 1
            langfuse_event(trace_id, "llm_error", metadata={"node": "attribute_matcher", "attempt": retries, "error": str(e)}, level="ERROR")
            if retries < MAX_RETRIES:
                return {"_attr_retries": retries}
            return {"_attr_done": True, "error_info": {"attr_failed": str(e)}}

        msgs = result.get("messages", [])
        attr_output = _extract_json(msgs, "attr_mapping")

        if attr_output:
            current = state.get("latest_result") or {}
            langfuse_event(trace_id, "attr_success", metadata={
                "mapping_count": len(attr_output.get("attr_mapping", [])),
            })
            return {
                "_attr_done": True,
                "latest_result": {
                    **current,
                    "attr_mapping": attr_output.get("attr_mapping", current.get("attr_mapping", [])),
                    "warning": attr_output.get("warning", current.get("warning", {"has_warn": False, "warn_content": ""})),
                    "suggestion": attr_output.get("suggestion", current.get("suggestion", {"summary": "", "items": []})),
                },
                "messages": msgs,
            }

        retries = retries_before + 1
        langfuse_event(trace_id, "parse_error", metadata={
            "node": "attribute_matcher", "attempt": retries, "max_retries": MAX_RETRIES,
            "error": "JSON 解析失败：缺少 attr_mapping 字段",
        })
        if retries < MAX_RETRIES:
            return {"_attr_retries": retries}
        return {"_attr_done": True, "error_info": {"attr_parse_failed": "JSON parse failed"}}
