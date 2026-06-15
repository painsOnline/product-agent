"""
文件名称：agent_executor.py
作者：shop-tool
时间：2026-06-15
逻辑说明：Agent 执行器，流式推送，从 AgentState 提取结构化结果.
"""
import asyncio
import json as _json
import logging
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from app.core.context import RequestContext
from app.core.monitor import AgentMonitor

logger = logging.getLogger(__name__)


class AgentExecutor:
    """封装 Agent 执行、流式推送和结果提取."""

    def __init__(self, ctx: RequestContext, monitor: AgentMonitor) -> None:
        self._ctx = ctx
        self._monitor = monitor

    async def execute(
        self,
        graph,
        input_state: dict,
        config: dict,
        origin_title: str,
    ) -> dict:
        await self._monitor.send_step(
            "agent", "running", "正在分析您的需求，调用子 Agent..."
        )

        seen_nodes: set[str] = set()
        _final_state_snapshot: Any = None

        try:
            async for chunk in graph.astream(
                input_state, config, stream_mode="updates"
            ):
                if chunk is None:
                    continue
                for node_name, node_output in chunk.items():
                    if node_output is None:
                        continue
                    if node_name not in seen_nodes:
                        seen_nodes.add(node_name)
                        if node_name == "title_optimizer":
                            asyncio.create_task(
                                self._monitor.send_step(
                                    "title_optimizer", "running", "正在优化商品标题..."
                                )
                            )
                        elif node_name == "attribute_matcher":
                            asyncio.create_task(
                                self._monitor.send_step(
                                    "attribute_matcher", "running", "正在匹配商品属性..."
                                )
                            )

                    msgs = node_output.get("messages", [])
                    for msg in msgs:
                        if isinstance(msg, (AIMessage, ToolMessage)):
                            content = getattr(msg, "content", "")
                            if content and isinstance(content, str):
                                asyncio.create_task(
                                    self._monitor.send_stream(content[:500])
                                )

                _final_state_snapshot = chunk
        except Exception:
            logger.exception("Graph execution failed, falling back to state extraction")
            await self._monitor.send_step(
                "agent", "failed", "Agent 执行异常，尝试从已有状态提取结果"
            )

        # 从 AgentState 提取结果
        try:
            state = await graph.aget_state(config)
            values = getattr(state, "values", state) or {}
            result = _extract(state, origin_title)
            result["_current_step"] = values.get("current_step", "confirm")
        except Exception:
            logger.exception("State extraction failed, using fallback")
            result = _fallback(origin_title, "状态提取失败")
            result["_current_step"] = "confirm"

        if result.get("new_title") and result["new_title"] != origin_title:
            await self._monitor.send_step("summarizing", "done", "结果汇总完成")
        else:
            logger.warning("Extracted result has no new_title or matches original: %s", result.get("title_note", ""))

        return result


def _extract(state: Any, origin_title: str) -> dict:
    """从 StateSnapshot 提取结果.

    优先级: latest_result → messages 中的 JSON.
    """
    if state is None:
        return _fallback(origin_title, "状态为空")

    values = getattr(state, "values", state) or {}

    # 方式1: latest_result（state_schema 直接写入）
    lr = values.get("latest_result")
    if lr and isinstance(lr, dict) and lr.get("new_title"):
        logger.info("Result extracted from latest_result: new_title=%s", lr["new_title"][:50])
        return lr

    # 方式2: messages 中最后一个含 new_title 的 JSON
    msgs = values.get("messages", [])
    for msg in reversed(msgs):
        content = getattr(msg, "content", "")
        if not isinstance(content, str) or "new_title" not in content:
            continue
        try:
            cleaned = content.strip()
            if cleaned.startswith("```"):
                idx = cleaned.find("\n")
                cleaned = cleaned[idx + 1:] if idx > 0 else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed = _json.loads(cleaned.strip())
            if isinstance(parsed, dict) and "new_title" in parsed:
                logger.info("Result extracted from messages JSON: new_title=%s", parsed["new_title"][:50])
                return parsed
        except Exception:
            pass

    logger.warning("No valid result found in state, messages count=%d, latest_result=%s",
                   len(msgs), "present" if lr else "absent")
    return _fallback(origin_title, "Agent 未返回结构化结果")


def _fallback(origin_title: str, reason: str) -> dict:
    return {
        "new_title": origin_title,
        "original_title": origin_title,
        "title_note": reason,
        "attr_mapping": [],
        "warning": {"has_warn": True, "warn_content": reason},
        "suggestion": {"summary": "", "items": []},
    }
