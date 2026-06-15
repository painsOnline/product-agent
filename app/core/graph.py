"""
文件名称：graph.py
作者：shop-tool
时间：2026-06-16
逻辑说明：StateGraph 构建器，组装节点和边.

START → supervisor
  → title_optimizer / attribute_matcher / chat_responder / summarize → END
"""
from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.entities.agent_state import AgentState
from app.nodes import (
    attribute_matcher_node,
    chat_responder_node,
    summarize_node,
    supervisor_node,
    title_optimizer_node,
)


def build_graph(
    sub_agents: dict[str, Any],
    checkpointer: Any = None,
) -> Any:
    """构建 Supervisor StateGraph."""
    builder = StateGraph(AgentState)

    builder.add_node("supervisor", partial(supervisor_node, sub_agents=sub_agents))
    builder.add_node("title_optimizer", partial(title_optimizer_node, sub_agents=sub_agents))
    builder.add_node("attribute_matcher", partial(attribute_matcher_node, sub_agents=sub_agents))
    builder.add_node("chat_responder", partial(chat_responder_node, sub_agents=sub_agents))
    builder.add_node("summarize", summarize_node)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        lambda s: s.get("_route", "end"),
        {
            "title": "title_optimizer",
            "attribute": "attribute_matcher",
            "chat_responder": "chat_responder",
            "summarize": "summarize",
            "end": END,
        },
    )
    builder.add_edge("title_optimizer", "supervisor")
    builder.add_edge("attribute_matcher", "supervisor")
    builder.add_edge("chat_responder", "supervisor")
    builder.add_edge("summarize", END)

    return builder.compile(checkpointer=checkpointer)
