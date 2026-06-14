"""
文件名称：chat_session.py
作者：shop-tool
时间：2026-06-14
逻辑说明：单次聊天会话，所有参数从 RequestContext 获取，不单独传递.
"""
from app.agent.main_agent import get_agent
from app.conf.constants import CHECKPOINT_PREFIX
from app.conf.settings import get_settings
from app.core.context import RequestContext
from app.core.monitor import AgentMonitor
from app.middlewares import discover_middlewares
from app.services.agent_executor import AgentExecutor
from app.services.chat_history_service import (
    build_agent_input,
    load_chat_history,
    save_assistant_message,
    save_confirm_reply,
    save_user_message,
)

settings = get_settings()


class ChatSession:
    """单次聊天会话，delegates 到 AgentExecutor 和 chat_history_service."""

    def __init__(self, ctx: RequestContext, monitor: AgentMonitor) -> None:
        self._ctx = ctx
        self._monitor = monitor
        self._executor = AgentExecutor(ctx, monitor)

    async def handle_chat(
        self,
        operate_type: str,
        origin_title: str,
        origin_attrs: list,
        user_content: str,
    ) -> None:
        ctx = self._ctx

        await self._monitor.send_step("history", "running", "正在加载历史对话...")
        await save_user_message(
            ctx,
            user_content=user_content,
            operate_type=operate_type,
            origin_title=origin_title,
            origin_attrs=origin_attrs,
        )
        history_msgs = await load_chat_history(ctx)
        await self._monitor.send_step(
            "history", "done", f"已加载 {len(history_msgs)} 条历史消息"
        )

        agent_messages = history_msgs + [
            {"role": "user", "content": build_agent_input(
                user_content, operate_type, origin_title, origin_attrs
            )}
        ]

        scoped_thread_id = f"{CHECKPOINT_PREFIX}{ctx.tenant_code}:{ctx.thread_id}"
        agent = get_agent(
            scoped_thread_id,
            llm_config=None,
            callbacks=discover_middlewares(),
            redis_client=await ctx.redis(),
        )
        config = {"configurable": {"thread_id": scoped_thread_id}}

        validated = await self._executor.execute(agent, agent_messages, config, origin_title)

        await self._monitor.send_step("summarizing", "done", "结果汇总完成")
        await self._monitor.send_final(validated)
        await save_assistant_message(ctx, validated)

        await self._monitor.send_confirm(
            thread_id=ctx.thread_id,
            import_product_id=ctx.import_product_id,
            user_id=ctx.user_id,
            timeout=settings.hitl_timeout,
            data=validated,
        )

    async def handle_confirm(self, operate_result: str) -> None:
        if operate_result == "confirm":
            await save_confirm_reply(self._ctx, "confirm")
            await self._monitor.send_result("修改已应用")
        else:
            await save_confirm_reply(self._ctx, "cancel")
            await self._monitor.send_result("已取消修改")
