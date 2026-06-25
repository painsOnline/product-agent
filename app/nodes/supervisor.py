"""
文件名称：supervisor.py
作者：shop-tool
时间：2026-06-15
逻辑说明：主管节点 — 调用意图识别子 Agent + 规则路由.
"""
import json as _json
import logging
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.conf.constants import OperateType
from app.core.langfuse_client import (
    create_callback_handler, get_trace_id, inject_callback, langfuse_event, langfuse_span,
)
from app.entities.agent_state import AgentState

logger = logging.getLogger(__name__)
_O = OperateType
MAX_RETRIES = 3

_VALID_ACTIONS = {_O.TITLE, _O.ATTRIBUTE, _O.BOTH, _O.CHAT}


def _parse_intent(raw: str) -> str:
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            idx = cleaned.find("\n")
            cleaned = cleaned[idx + 1:] if idx > 0 else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        obj = _json.loads(cleaned.strip())
        action = str(obj.get("action", "")).strip().lower()
        if action in _VALID_ACTIONS:
            return action
    except Exception:
        pass
    return ""


async def _detect_intent(state, config, sub_agents):
    agent = sub_agents.get("intent_detector")
    if agent is None:
        return state.get("operate_type", _O.BOTH)
    handler = create_callback_handler()
    _config = inject_callback(config, handler)
    try:
        result = await agent.ainvoke(state, _config)
    except Exception:
        logger.exception("Intent detection failed")
        return state.get("operate_type", _O.BOTH)
    msgs = result.get("messages", [])
    for msg in reversed(msgs):
        content = getattr(msg, "content", "")
        if not isinstance(content, str) or "action" not in content:
            continue
        action = _parse_intent(content)
        if action:
            return action
    return state.get("operate_type", _O.BOTH)


async def supervisor_node(
    state: AgentState, config: RunnableConfig, *, sub_agents: dict[str, Any] | None = None
) -> dict[str, Any]:
    sub_agents = sub_agents or {}
    operate_type = state.get("operate_type", _O.BOTH)
    title_done = state.get("_title_done", False)
    attr_done = state.get("_attr_done", False)
    trace_id = get_trace_id()

    with langfuse_span("supervisor", input_data={
        "operate_type": operate_type, "intent": state.get("_intent", "initial"),
        "title_done": title_done, "attr_done": attr_done,
    }):
        intent: str = state.get("_intent", "")
        if not intent:
            intent = await _detect_intent(state, config, sub_agents)
            if intent == _O.CHAT:
                langfuse_event(trace_id, "route", metadata={"decision": "chat_responder", "intent": intent})
                return {"_intent": _O.CHAT, "operate_type": _O.CHAT, "_route": "chat_responder", "current_step": "chatting"}
            if intent in (_O.TITLE, _O.ATTRIBUTE, _O.BOTH):
                operate_type = _O.INTENT_TO_OPERATE.get(intent, intent)

        if intent == _O.CHAT and state.get("_chat_done", False):
            langfuse_event(trace_id, "route", metadata={"decision": "summarize", "intent": _O.CHAT})
            return {"_route": "summarize", "current_step": "summarizing"}

        title_retries = state.get("_title_retries", 0)
        attr_retries = state.get("_attr_retries", 0)
        target_attrs = state.get("target_attrs", [])

        need_title = (operate_type in (_O.REWRITE_TITLE, _O.BOTH, _O.TITLE)
                      and not title_done and title_retries < MAX_RETRIES)
        need_attr = (operate_type in (_O.MATCH_ATTR, _O.BOTH, _O.ATTRIBUTE)
                     and not attr_done and attr_retries < MAX_RETRIES and bool(target_attrs))

        langfuse_event(trace_id, "state_snapshot", metadata={
            "title_done": title_done, "attr_done": attr_done,
            "title_retries": title_retries, "attr_retries": attr_retries,
        })

        route_map = _O.ROUTE_MAP
        updates: dict[str, Any] = {"_intent": intent, "operate_type": operate_type}
        if need_title:
            updates["_route"] = route_map.get(_O.REWRITE_TITLE, "title")
            updates["current_step"] = "title_optimizing"
            route = "title_optimizer"
        elif need_attr:
            updates["_route"] = route_map.get(_O.MATCH_ATTR, "attribute")
            updates["current_step"] = "attribute_matching"
            route = "attribute_matcher"
        else:
            updates["_route"] = "summarize"
            updates["current_step"] = "summarizing"
            route = "summarize"

        langfuse_event(trace_id, "route", metadata={"decision": route, "intent": intent})
        return updates
