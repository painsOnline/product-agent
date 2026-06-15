"""
文件名称：chat_responder.py
作者：shop-tool
时间：2026-06-16
逻辑说明：聊天响应节点 — 调用 chat_responder 子 Agent，提取回复文本.
"""
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from app.entities.agent_state import AgentState

logger = logging.getLogger(__name__)


def _build_task_message(state: AgentState) -> HumanMessage:
    """从 state 构造聊天上下文."""
    user_content = state.get("user_content", "")
    original_title = state.get("original_title", "")
    original_attrs = state.get("original_attrs", [])
    latest_result = state.get("latest_result") or {}

    parts = [f"用户提问: {user_content}"]
    if original_title:
        parts.append(f"当前商品标题: {original_title}")
    if original_attrs:
        import json as _json
        parts.append(f"当前商品属性: {_json.dumps(original_attrs, ensure_ascii=False)}")
    if latest_result.get("new_title"):
        parts.append(f"已优化的标题: {latest_result['new_title']}")
        parts.append(f"优化说明: {latest_result.get('title_note', '')}")
    if latest_result.get("attr_mapping"):
        import json as _json
        parts.append(f"已匹配的属性: {_json.dumps(latest_result['attr_mapping'], ensure_ascii=False)}")
    parts.append("请根据上述信息回答用户的问题。")
    return HumanMessage(content="\n".join(parts))


async def chat_responder_node(
    state: AgentState, config: RunnableConfig, *, sub_agents: dict[str, Any] | None = None
) -> dict[str, Any]:
    """聊天响应节点：调用 chat_responder 子 Agent，提取回复."""
    sub_agents = sub_agents or {}
    agent = sub_agents.get("chat_responder")
    if agent is None:
        return {"_chat_done": True}

    task_input = {
        **state,
        "messages": list(state.get("messages", [])) + [_build_task_message(state)],
    }

    try:
        result = await agent.ainvoke(task_input, config)
    except Exception as e:
        logger.warning("chat_responder failed: %s", e)
        return {"_chat_done": True}

    msgs = result.get("messages", [])
    reply = ""
    is_rejected = False
    for msg in reversed(msgs):
        content = getattr(msg, "content", "")
        if not isinstance(content, str) or not content.strip():
            continue
        try:
            cleaned = content.strip()
            if cleaned.startswith("```"):
                idx = cleaned.find("\n")
                cleaned = cleaned[idx + 1:] if idx > 0 else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            import json as _json
            parsed = _json.loads(cleaned.strip())
            if isinstance(parsed, dict) and "reply" in parsed:
                reply = parsed.get("reply", content)
                is_rejected = parsed.get("is_rejected", False)
                break
        except Exception:
            reply = content.strip()
            break

    # 不返回 messages — 聊天回复仅通过 respond WS 消息发送，不走 stream
    return {
        "_chat_done": True,
        "latest_result": {
            **(state.get("latest_result") or {}),
            "chat_reply": reply,
            "chat_is_rejected": is_rejected,
        },
    }
