"""
文件名称：agent_executor.py
作者：shop-tool
时间：2026-06-15
逻辑说明：Agent 执行器，流式推送，从 AgentState 提取结构化结果.
"""
import json as _json
import logging
from typing import Any

from app.conf.constants import OperateType as _O
from app.core.context import RequestContext
from app.core.langfuse_client import langfuse_event
from app.core.monitor import AgentMonitor

logger = logging.getLogger(__name__)

_NODE_LABELS: dict[str, tuple[str, str]] = {
    "supervisor": ("agent", "正在分析需求并规划执行路径..."),
    "title_optimizer": ("title_optimizer", "正在优化商品标题，预计需要 10~30 秒..."),
    "attribute_matcher": ("attribute_matcher", "正在匹配商品属性，预计需要 10~30 秒..."),
    "chat_responder": ("chat_responder", "正在分析您的问题..."),
    "summarize": ("summarizing", "正在汇总结果..."),
}

# JSON 输出节点：等待完整 JSON 再发送，不逐字流式
_JSON_NODES = {"supervisor", "title_optimizer", "attribute_matcher"}


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
        from app.core.langfuse_client import get_trace_id
        trace_id = get_trace_id()

        await self._monitor.send_step(
            "agent", "running", "正在启动 Agent，分析您的需求..."
        )

        _stream_buf = ""
        _stream_sent_len = 0
        _current_node = ""

        try:
            async for event in graph.astream_events(input_state, config, version="v2"):
                kind = event.get("event", "")
                name = event.get("name", "")

                if kind == "on_chain_start" and name in _NODE_LABELS:
                    _stream_buf = ""
                    _stream_sent_len = 0
                    _current_node = name
                    step_key, detail = _NODE_LABELS[name]
                    await self._monitor.send_step(step_key, "running", detail)

                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk is None:
                        continue
                    content = getattr(chunk, "content", "")
                    if not content or not isinstance(content, str):
                        continue

                    _stream_buf += content

                    if _current_node in _JSON_NODES:
                        # JSON 节点：只缓冲，等节点完成一次性发送完整 JSON
                        pass
                    else:
                        # 文字节点（chat_responder）：逐段流式推送
                        if len(_stream_buf) - _stream_sent_len >= 20:
                            await self._monitor.send_stream(_stream_buf)
                            _stream_sent_len = len(_stream_buf)

                elif kind == "on_chain_end" and name in _NODE_LABELS:
                    if _current_node in _JSON_NODES:
                        # JSON 节点：发送完整输出
                        if _stream_buf:
                            await self._monitor.send_stream(_stream_buf)
                    else:
                        # 文字节点：发送剩余内容
                        if _stream_buf and len(_stream_buf) > _stream_sent_len:
                            await self._monitor.send_stream(_stream_buf)

                    step_key, _ = _NODE_LABELS[name]
                    await self._monitor.send_step(step_key, "done", "")
                    langfuse_event(
                        trace_id, "node_completed",
                        metadata={"node": name},
                    )
                    _current_node = ""

        except Exception:
            logger.exception("Graph execution failed, falling back to state extraction")
            langfuse_event(
                trace_id, "error",
                metadata={"stage": "graph_execution", "error": "Graph 执行异常"},
                level="ERROR",
            )
            await self._monitor.send_step(
                "agent", "failed", "Agent 执行异常，尝试从已有状态提取结果"
            )

        # 从 AgentState 提取结果
        try:
            state = await graph.aget_state(config)
            values = getattr(state, "values", state) or {}
            result = _extract(state, origin_title)
            result["_current_step"] = values.get("current_step", "confirm")
            # supervisor 通过 operate_type 传递用户意图，供前端决定展示内容
            result["operate_type"] = values.get("operate_type", _O.BOTH)
        except Exception:
            logger.exception("State extraction failed, using fallback")
            langfuse_event(
                trace_id, "error",
                metadata={"stage": "state_extraction", "error": "状态提取失败"},
                level="ERROR",
            )
            result = _fallback(origin_title, "状态提取失败")
            result["_current_step"] = "confirm"
            result["operate_type"] = _O.BOTH

        if result.get("new_title") and result["new_title"] != origin_title:
            await self._monitor.send_step("summarizing", "done", "结果汇总完成")
        else:
            logger.warning("Extracted result has no new_title or matches original: %s", result.get("title_note", ""))

        langfuse_event(
            trace_id, "node_completed",
            metadata={"node": "summarize", "new_title": result.get("new_title", "")[:100]},
        )

        return result


def _extract(state: Any, origin_title: str) -> dict:
    """从 StateSnapshot 提取结果.

    优先级: latest_result → messages 中的 JSON.
    """
    if state is None:
        return _fallback(origin_title, "状态为空")

    values = getattr(state, "values", state) or {}

    lr = values.get("latest_result")
    if lr and isinstance(lr, dict) and lr.get("new_title"):
        logger.info("Result extracted from latest_result: new_title=%s", lr["new_title"][:50])
        return lr

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
