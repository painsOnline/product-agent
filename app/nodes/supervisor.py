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

from app.entities.agent_state import AgentState

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _parse_intent(raw: str) -> str:
    """从 LLM 返回解析意图 action."""
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            idx = cleaned.find("\n")
            cleaned = cleaned[idx + 1:] if idx > 0 else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        obj = _json.loads(cleaned.strip())
        action = str(obj.get("action", "")).strip().lower()
        if action in ("title", "attribute", "both", "chat"):
            return action
    except Exception:
        pass
    return ""


async def _detect_intent(
    state: AgentState, config: RunnableConfig, sub_agents: dict[str, Any]
) -> str:
    """调用 intent_detector 子 Agent 判断用户意图."""
    agent = sub_agents.get("intent_detector")
    if agent is None:
        return state.get("operate_type", "both")

    try:
        result = await agent.ainvoke(state, config)
    except Exception:
        logger.exception("Intent detection failed, falling back to operate_type")
        return state.get("operate_type", "both")

    msgs = result.get("messages", [])
    for msg in reversed(msgs):
        content = getattr(msg, "content", "")
        if not isinstance(content, str) or "action" not in content:
            continue
        action = _parse_intent(content)
        if action:
            logger.info("Intent detected: %s", action)
            return action

    logger.warning("Intent not found in messages, falling back to operate_type")
    return state.get("operate_type", "both")


async def supervisor_node(
    state: AgentState, config: RunnableConfig, *, sub_agents: dict[str, Any] | None = None
) -> dict[str, Any]:
    """主管节点：首次调用意图识别子 Agent，后续规则路由."""
    sub_agents = sub_agents or {}
    operate_type = state.get("operate_type", "both")
    title_done = state.get("_title_done", False)
    attr_done = state.get("_attr_done", False)

    # 首次调用：意图识别
    intent: str = state.get("_intent", "")
    if not intent:
        intent = await _detect_intent(state, config, sub_agents)
        if intent == "chat":
            return {
                "_intent": "chat",
                "_route": "chat_responder",
                "current_step": "chatting",
            }
        if intent in ("title", "attribute", "both"):
            operate_type = intent

    # chat 意图完成 → 直接结束
    if intent == "chat" and state.get("_chat_done", False):
        return {"_route": "summarize", "current_step": "summarizing"}

    title_retries = state.get("_title_retries", 0)
    attr_retries = state.get("_attr_retries", 0)
    target_attrs = state.get("target_attrs", [])

    need_title = (
        operate_type in ("rewrite_title", "both", "title")
        and not title_done
        and title_retries < MAX_RETRIES
    )
    need_attr = (
        operate_type in ("match_attr", "both", "attribute")
        and not attr_done
        and attr_retries < MAX_RETRIES
        and bool(target_attrs)
    )

    updates: dict[str, Any] = {"_intent": intent}
    if need_title:
        updates["_route"] = "title"
        updates["current_step"] = "title_optimizing"
    elif need_attr:
        updates["_route"] = "attribute"
        updates["current_step"] = "attribute_matching"
    else:
        updates["_route"] = "summarize"
        updates["current_step"] = "summarizing"
    return updates
