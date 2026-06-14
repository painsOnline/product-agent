"""
文件名称：logging.py
作者：shop-tool
时间：2026-06-14
逻辑说明：LLM 调用日志中间件，通过 auto-discovery 自动加载.

依赖从 RequestContext.current() 获取，无需外部传参.
"""
import asyncio
import logging
import time
import uuid
from typing import Any

from langchain_core.outputs import LLMResult

from app.conf.constants import ActionStatus, ActionType
from app.middlewares.base import BaseMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """记录 LLM 调用日志到 t_agent_action_logs."""

    def __init__(self) -> None:
        super().__init__()
        self._call_times: dict[str, float] = {}

    # ---- LangChain 回调钩子 ----

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        self._call_times[str(kwargs.get("run_id", uuid.uuid4()))] = time.time()

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        run_id = str(kwargs.get("run_id", ""))
        start = self._call_times.pop(run_id, time.time())
        cost_ms = int((time.time() - start) * 1000)

        token_usage = {}
        if response.llm_output and "token_usage" in response.llm_output:
            token_usage = response.llm_output["token_usage"]

        self._schedule_save(
            action_type=ActionType.LLM_INVOKE,
            status=ActionStatus.SUCCESS,
            request_data={
                "prompts_count": len(response.generations) if response.generations else 0
            },
            response_data={
                "generations_count": len(response.generations) if response.generations else 0
            },
            metadata={
                "cost_ms": cost_ms,
                "input_tokens": token_usage.get("prompt_tokens", 0),
                "output_tokens": token_usage.get("completion_tokens", 0),
            },
        )

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        run_id = str(kwargs.get("run_id", ""))
        start = self._call_times.pop(run_id, time.time())
        cost_ms = int((time.time() - start) * 1000)

        self._schedule_save(
            action_type=(
                ActionType.LLM_TIMEOUT
                if "timeout" in str(error).lower()
                else ActionType.PARSE_ERROR
            ),
            status=ActionStatus.FAILURE,
            request_data={"error": str(error)},
            response_data={},
            metadata={"cost_ms": cost_ms},
        )

    # ---- 持久化 ----

    def _schedule_save(
        self,
        action_type: str,
        status: str,
        request_data: dict,
        response_data: dict,
        metadata: dict,
    ) -> None:
        """调度异步写入（回调钩子中不能 await）."""
        from app.core.context import RequestContext
        from app.services.action_log_writer import write_action_log

        ctx = RequestContext.current()
        if ctx is None or not ctx.user_id:
            return
        if ctx.tenant_db() is None:
            return

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(
                    write_action_log(
                        ctx,
                        action_type=action_type,
                        status=status,
                        request_data=request_data,
                        response_data=response_data,
                        metadata=metadata,
                    )
                )
        except Exception as e:
            logger.error("Failed to schedule action log: %s", e)
