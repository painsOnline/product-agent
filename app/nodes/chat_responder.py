"""
文件名称：chat_responder.py
作者：shop-tool
时间：2026-06-16
逻辑说明：聊天响应节点.
"""
import json as _json
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from app.core.langfuse_client import create_callback_handler, inject_callback, langfuse_span
from app.entities.agent_state import AgentState

logger = logging.getLogger(__name__)


def _build_task_message(state: AgentState) -> HumanMessage:
    user_content = state.get("user_content", "")
    original_title = state.get("original_title", "")
    original_attrs = state.get("original_attrs", [])
    lr = state.get("latest_result") or {}
    parts = [f"用户提问: {user_content}"]
    if original_title:
        parts.append(f"当前商品标题: {original_title}")
    if original_attrs:
        parts.append(f"当前商品属性: {_json.dumps(original_attrs, ensure_ascii=False)}")
    if lr.get("new_title"):
        parts.append(f"已优化的标题: {lr['new_title']}")
    if lr.get("attr_mapping"):
        parts.append(f"已匹配的属性: {_json.dumps(lr['attr_mapping'], ensure_ascii=False)}")
    parts.append("请根据上述信息回答用户的问题。")
    return HumanMessage(content="\n".join(parts))


async def chat_responder_node(
    state: AgentState, config: RunnableConfig, *, sub_agents: dict[str, Any] | None = None
) -> dict[str, Any]:
    sub_agents = sub_agents or {}
    agent = sub_agents.get("chat_responder")
    if agent is None:
        return {"_chat_done": True}

    task_msg = _build_task_message(state)

    with langfuse_span("chat_responder", input_data={
        "user_content": state.get("user_content", ""),
    }):
        task_input = {**state, "messages": list(state.get("messages", [])) + [task_msg]}
        handler = create_callback_handler()
        _config = inject_callback(config, handler)

        try:
            result = await agent.ainvoke(task_input, _config)
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
                parsed = _json.loads(cleaned.strip())
                if isinstance(parsed, dict) and "reply" in parsed:
                    reply = parsed.get("reply", content)
                    is_rejected = parsed.get("is_rejected", False)
                    break
            except Exception:
                reply = content.strip()
                break

        return {
            "_chat_done": True,
            "latest_result": {
                **(state.get("latest_result") or {}),
                "chat_reply": reply, "chat_is_rejected": is_rejected,
            },
        }
