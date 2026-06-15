"""
文件名称：chat_session.py
作者：shop-tool
时间：2026-06-14
逻辑说明：单次聊天会话 — origin_title/original_attrs 从 DB 加载，target_attrs 前端传.
"""
from app.agent.main_agent import get_agent
from app.core.state_factory import StateFactory
from app.conf.constants import CHECKPOINT_PREFIX
from app.conf.settings import get_settings
from app.core.context import RequestContext
from app.core.monitor import AgentMonitor
from app.repositories.llm_config_repo import get_active_config_dict
from app.repositories.product_repo import get_by_id
from app.services.agent_executor import AgentExecutor
from app.services.chat_history_service import (
    save_assistant_message,
    save_confirm_reply,
    save_user_message,
)
import uuid

settings = get_settings()
_state_factory = StateFactory()


class ChatSession:
    """单次聊天会话."""

    def __init__(self, ctx: RequestContext, monitor: AgentMonitor) -> None:
        self._ctx = ctx
        self._monitor = monitor
        self._executor = AgentExecutor(ctx, monitor)

    async def handle_chat(
        self,
        operate_type: str,
        target_attrs: list,
        user_content: str,
        manual_data: dict | None = None,
    ) -> None:
        ctx = self._ctx
        db = ctx.tenant_db()
        if db is None:
            await self._monitor.send_error("500", "租户库未初始化")
            return

        # 从 DB 加载 origin 数据
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
        await save_user_message(
            ctx,
            user_content=user_content,
            operate_type=operate_type,
            original_title=origin_title,
            original_attrs=original_attrs,
            target_attrs=target_attrs,
            manual_data=manual_data,
        )
        # 历史记录已改为独立 REST 接口，WS 不再返回历史
        await self._monitor.send_step("history", "done", "准备就绪")

        input_state = _state_factory.chat(
            thread_id=ctx.thread_id,
            user_id=ctx.user_id,
            import_product_id=ctx.import_product_id,
            operate_type=operate_type,
            original_title=origin_title,
            original_attrs=original_attrs,
            target_attrs=target_attrs,
            user_content=user_content,
            manual_data=manual_data,
        )

        scoped_thread_id = f"{CHECKPOINT_PREFIX}{ctx.tenant_code}:{ctx.thread_id}"

        llm_config = await get_active_config_dict(db)
        if not llm_config:
            await self._monitor.send_error("500", "未找到 LLM 配置")
            return

        agent = get_agent(
            scoped_thread_id,
            llm_config=llm_config,
            redis_client=await ctx.redis(),
        )
        await agent.checkpointer.adelete_thread(scoped_thread_id)
        config = {
            "configurable": {"thread_id": scoped_thread_id},
            "recursion_limit": 15,
        }

        try:
            validated = await self._executor.execute(
                agent, input_state, config, origin_title
            )
        except Exception:
            logger.exception("Agent execution failed")
            await self._monitor.send_error("500", "Agent 执行失败，请重试")
            return

        current_step = validated.pop("_current_step", "confirm")

        # 聊天问询回答：发 respond，不发 final/confirm
        if current_step == "finished":
            await self._monitor.send_respond(
                reply=validated.get("chat_reply", validated.get("title_note", "")),
                is_rejected=False,
            )
            await save_assistant_message(ctx, validated)
            return

        await self._monitor.send_final(validated)
        await save_assistant_message(ctx, validated)

        await self._monitor.send_confirm(
            thread_id=ctx.thread_id,
            import_product_id=ctx.import_product_id,
            user_id=ctx.user_id,
            timeout=settings.hitl_timeout,
            data=validated,
        )

    async def handle_confirm(
        self, operate_result: str, payload: dict | None = None
    ) -> None:
        if operate_result == "confirm":
            await save_confirm_reply(self._ctx, "confirm", payload=payload)
            await self._monitor.send_result("修改已应用")
        else:
            await save_confirm_reply(self._ctx, "cancel")
            await self._monitor.send_result("已取消修改")
