"""
文件名称：chat_session.py
作者：shop-tool
时间：2026-06-14
逻辑说明：单次聊天会话.
"""
import logging
import uuid

from app.agent.main_agent import get_agent
from app.conf.constants import CHECKPOINT_PREFIX
from app.conf.settings import get_settings
from app.core.context import RequestContext
from app.core.langfuse_client import flush_langfuse, get_langfuse, langfuse_event
from app.core.monitor import AgentMonitor
from app.repositories.llm_config_repo import get_active_config_dict
from app.repositories.product_repo import get_by_id
from app.services.agent_executor import AgentExecutor
from app.services.chat_history_service import save_assistant_message, save_confirm_reply, save_user_message

logger = logging.getLogger(__name__)
settings = get_settings()
_state_factory = None


def _get_state_factory():
    global _state_factory
    if _state_factory is None:
        from app.core.state_factory import StateFactory
        _state_factory = StateFactory()
    return _state_factory


class ChatSession:

    def __init__(self, ctx: RequestContext, monitor: AgentMonitor) -> None:
        self._ctx = ctx
        self._monitor = monitor
        self._executor = AgentExecutor(ctx, monitor)

    async def handle_chat(self, operate_type: str, target_attrs: list,
                          user_content: str, manual_data: dict | None = None) -> None:
        ctx = self._ctx
        db = ctx.tenant_db()
        if db is None:
            await self._monitor.send_error("500", "租户库未初始化")
            return

        origin_title = ""
        original_attrs: list = []
        if ctx.import_product_id:
            try:
                pid = uuid.UUID(ctx.import_product_id)
                product = await get_by_id(db, pid)
                if product:
                    origin_title = product.ext_product_name or ""
                    original_attrs = product.attrs or []
            except (ValueError, Exception):
                pass

        await self._monitor.send_step("history", "running", "正在加载历史对话...")
        await save_user_message(ctx, user_content=user_content, operate_type=operate_type,
                                original_title=origin_title, original_attrs=original_attrs,
                                target_attrs=target_attrs, manual_data=manual_data)
        await self._monitor.send_step("history", "done", "准备就绪")

        langfuse_event(ctx.langfuse_trace_id, "user_message",
                       metadata={"user_content": user_content, "operate_type": operate_type})

        input_state = _get_state_factory().chat(
            thread_id=ctx.thread_id, user_id=ctx.user_id, import_product_id=ctx.import_product_id,
            operate_type=operate_type, original_title=origin_title, original_attrs=original_attrs,
            target_attrs=target_attrs, user_content=user_content, manual_data=manual_data,
        )

        llm_config = await get_active_config_dict(db)
        if not llm_config:
            await self._monitor.send_error("500", "未找到 LLM 配置")
            return

        scoped_thread_id = f"{CHECKPOINT_PREFIX}{ctx.tenant_code}:{ctx.thread_id}"
        agent = get_agent(scoped_thread_id, llm_config=llm_config, redis_client=await ctx.redis())
        await agent.checkpointer.adelete_thread(scoped_thread_id)
        config = {"configurable": {"thread_id": scoped_thread_id}, "recursion_limit": 15}

        validated: dict = {}
        try:
            validated = await self._executor.execute(agent, input_state, config, origin_title)
        except Exception:
            logger.exception("Agent execution failed")
            langfuse_event(ctx.langfuse_trace_id, "error",
                           metadata={"stage": "agent_execution"}, level="ERROR")
            await self._monitor.send_error("500", "Agent 执行失败，请重试")
            return

        current_step = validated.pop("_current_step", "confirm")

        if current_step == "finished":
            await self._monitor.send_respond(
                reply=validated.get("chat_reply", validated.get("title_note", "")),
                is_rejected=False)
            await save_assistant_message(ctx, validated)
            langfuse_event(ctx.langfuse_trace_id, "final_response",
                           metadata={"type": "chat", "is_rejected": False})
            return

        await self._monitor.send_final(validated)
        await save_assistant_message(ctx, validated)

        langfuse_event(ctx.langfuse_trace_id, "final_output", metadata={
            "new_title": validated.get("new_title", ""),
            "attr_mapping_count": len(validated.get("attr_mapping", [])),
        })

        await self._monitor.send_confirm(
            thread_id=ctx.thread_id, import_product_id=ctx.import_product_id,
            user_id=ctx.user_id, timeout=settings.hitl_timeout, data=validated)

        # HITL Span
        lf = get_langfuse()
        if lf and ctx.langfuse_trace_id:
            try:
                hitl_span = lf.start_observation(
                    trace_context={"trace_id": ctx.langfuse_trace_id},
                    name="hitl", as_type="span",
                    input={"timeout_seconds": settings.hitl_timeout,
                           "new_title": validated.get("new_title")},
                )
                ctx.langfuse_hitl_span = hitl_span
            except Exception:
                pass

        flush_langfuse()

    async def handle_confirm(self, operate_result: str, payload: dict | None = None) -> None:
        ctx = self._ctx
        if operate_result == "confirm":
            await save_confirm_reply(self._ctx, "confirm", payload=payload)
            await self._monitor.send_result("修改已应用")
        else:
            await save_confirm_reply(self._ctx, "cancel")
            await self._monitor.send_result("已取消修改")

        hitl_span = ctx.langfuse_hitl_span
        if hitl_span is not None:
            try:
                hitl_span.update(output={"operate_result": operate_result})
                hitl_span.end()
            except Exception:
                pass

        langfuse_event(ctx.langfuse_trace_id, f"hitl_{operate_result}",
                       metadata={"operate_result": operate_result})
        flush_langfuse()
