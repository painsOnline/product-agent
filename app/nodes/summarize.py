"""
文件名称：summarize.py
作者：shop-tool
时间：2026-06-15
逻辑说明：汇总节点 — 合并 title + attr 结果到 latest_result.
"""
from typing import Any

from app.entities.agent_state import AgentState


def summarize_node(state: AgentState) -> dict[str, Any]:
    """汇总节点：合并 title + attr 结果到 latest_result.

    chat 意图跳过确认，直接 finished.
    """
    lr = state.get("latest_result", {})
    origin_title = state.get("original_title", "")
    intent = state.get("_intent", "")

    if intent == "chat":
        return {
            "latest_result": {
                "new_title": origin_title,
                "original_title": origin_title,
                "title_note": lr.get("chat_reply", lr.get("title_note", "")),
                "chat_reply": lr.get("chat_reply", ""),
                "attr_mapping": [],
                "warning": {"has_warn": False, "warn_content": ""},
                "suggestion": {"summary": "", "items": []},
            },
            "current_step": "finished",
        }

    return {
        "latest_result": {
            "new_title": lr.get("new_title", origin_title),
            "original_title": origin_title,
            "title_note": lr.get("title_note", "Agent 未返回有效结果"),
            "attr_mapping": lr.get("attr_mapping", []),
            "warning": lr.get("warning", {"has_warn": False, "warn_content": ""}),
            "suggestion": lr.get("suggestion", {"summary": "", "items": []}),
        },
        "current_step": "confirm",
    }
