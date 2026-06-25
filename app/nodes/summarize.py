"""
文件名称：summarize.py
作者：shop-tool
时间：2026-06-15
逻辑说明：汇总节点.
"""
from typing import Any

from app.conf.constants import OperateType
from app.core.langfuse_client import get_trace_id, langfuse_event, langfuse_span
from app.entities.agent_state import AgentState

_O = OperateType


def summarize_node(state: AgentState) -> dict[str, Any]:
    lr = state.get("latest_result", {})
    origin_title = state.get("original_title", "")
    # supervisor 通过 operate_type 显式传递识别到的用户意图
    intent = state.get("operate_type", state.get("_intent", _O.BOTH))
    trace_id = get_trace_id()

    with langfuse_span("summarize", input_data={
        "intent": intent,
        "has_title_result": "new_title" in lr,
        "has_attr_result": "attr_mapping" in lr,
    }):
        if intent == _O.CHAT:
            result = {
                "latest_result": {
                    "new_title": origin_title, "original_title": origin_title,
                    "title_note": lr.get("chat_reply", lr.get("title_note", "")),
                    "chat_reply": lr.get("chat_reply", ""), "attr_mapping": [],
                    "warning": {"has_warn": False, "warn_content": ""},
                    "suggestion": {"summary": "", "items": []},
                },
                "current_step": "finished",
            }
        elif intent in (_O.REWRITE_TITLE, _O.TITLE):
            result = {
                "latest_result": {
                    "new_title": lr.get("new_title", origin_title),
                    "original_title": origin_title,
                    "title_note": lr.get("title_note", "Agent 未返回有效结果"),
                    "attr_mapping": [],
                    "warning": lr.get("warning", {"has_warn": False, "warn_content": ""}),
                    "suggestion": lr.get("suggestion", {"summary": "", "items": []}),
                },
                "current_step": "confirm",
            }
        elif intent in (_O.MATCH_ATTR, _O.ATTRIBUTE):
            result = {
                "latest_result": {
                    "new_title": origin_title,
                    "original_title": origin_title,
                    "title_note": "",
                    "attr_mapping": lr.get("attr_mapping", []),
                    "warning": lr.get("warning", {"has_warn": False, "warn_content": ""}),
                    "suggestion": lr.get("suggestion", {"summary": "", "items": []}),
                },
                "current_step": "confirm",
            }
        else:
            # _O.BOTH 或未知：合并标题和属性结果
            result = {
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

        final = result["latest_result"]
        langfuse_event(trace_id, "final_output", metadata={
            "new_title": final.get("new_title", ""),
            "attr_mapping_count": len(final.get("attr_mapping", [])),
            "current_step": result.get("current_step"),
        })
        return result
