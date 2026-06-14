"""
文件名称：agent_executor.py
作者：shop-tool
时间：2026-06-14
逻辑说明：Agent 执行器，thread_id/user_id 从 RequestContext 获取.
"""
import asyncio
from typing import Any

from app.conf.constants import StatusCode
from app.core.context import RequestContext
from app.core.monitor import AgentMonitor
from app.entities.agent import SupervisorOutput


class AgentExecutor:
    """封装 Agent 执行、流式推送和输出校验."""

    def __init__(self, ctx: RequestContext, monitor: AgentMonitor) -> None:
        self._ctx = ctx
        self._monitor = monitor

    async def execute(
        self,
        agent,
        messages: list[dict],
        config: dict,
        origin_title: str,
    ) -> dict:
        await self._monitor.send_step(
            "agent", "running", "正在分析您的需求，调用子 Agent..."
        )
        final_output = None
        seen_nodes: set[str] = set()

        async for chunk in agent.astream(
            {"messages": messages}, config=config, stream_mode="updates"
        ):
            for node_name, state_update in chunk.items():
                self._on_node_start(node_name, seen_nodes)
                self._push_stream(state_update)
                final_output = self._collect_final(node_name, state_update, final_output)

        self._mark_nodes_done(seen_nodes)
        return self._validate_output(final_output, origin_title)

    def _on_node_start(self, node_name: str, seen: set[str]) -> None:
        node_steps = {
            "title-optimizer": ("title_optimizer", "running", "正在优化商品标题..."),
            "attribute-matcher": ("attribute_matcher", "running", "正在匹配商品属性..."),
        }
        if node_name in seen:
            return
        seen.add(node_name)
        if node_name in node_steps:
            step, status, detail = node_steps[node_name]
            asyncio.create_task(self._monitor.send_step(step, status, detail))
        elif node_name in ("supervisor", "__end__"):
            asyncio.create_task(
                self._monitor.send_step("summarizing", "running", "正在汇总结果...")
            )

    def _push_stream(self, state_update: dict) -> None:
        if "messages" not in state_update:
            return
        msgs = state_update["messages"]
        if not msgs:
            return
        last_msg = msgs[-1] if isinstance(msgs, list) else msgs
        content = getattr(last_msg, "content", "")
        if content and not isinstance(content, list):
            asyncio.create_task(self._monitor.send_stream(str(content)))

    def _mark_nodes_done(self, seen: set[str]) -> None:
        for node in ("title-optimizer", "attribute-matcher"):
            if node in seen:
                asyncio.create_task(
                    self._monitor.send_step(node.replace("-", "_"), "done", "执行完成")
                )

    @staticmethod
    def _collect_final(node_name: str, state_update: dict, current: Any) -> Any:
        if node_name not in ("supervisor", "__end__"):
            return current
        if "structured_response" in state_update:
            return state_update["structured_response"]
        if "messages" in state_update:
            msgs = state_update["messages"]
            if msgs:
                last = msgs[-1] if isinstance(msgs, list) else msgs
                return getattr(last, "content", None)
        return current

    def _validate_output(self, final_output: Any, origin_title: str) -> dict:
        if isinstance(final_output, dict):
            return final_output
        if isinstance(final_output, str):
            try:
                return SupervisorOutput.model_validate_json(final_output).model_dump()
            except Exception:
                asyncio.create_task(
                    self._monitor.send_error(StatusCode.PARSE_ERROR, "LLM 返回格式异常")
                )
        else:
            asyncio.create_task(self._monitor.send_step("summarizing", "failed", "无输出"))
        return {
            "new_title": origin_title,
            "title_note": "LLM 返回格式异常" if isinstance(final_output, str) else "无输出",
            "import_product_id": self._ctx.import_product_id,
            "thread_id": self._ctx.thread_id,
            "user_id": self._ctx.user_id,
            "attr_mapping": [],
            "warning": {
                "has_warn": isinstance(final_output, str),
                "warn_content": "输出校验失败" if isinstance(final_output, str) else "",
            },
            "suggestion": {"summary": "", "items": []},
        }
