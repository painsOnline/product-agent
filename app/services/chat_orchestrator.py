"""
文件名称：chat_orchestrator.py
作者：shop-tool
时间：2026-06-14
逻辑说明：WebSocket 连接生命周期管理.
"""
import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.agent.main_agent import remove_agent
from app.conf.constants import OperateType as _O, StatusCode, WS_HEARTBEAT_INTERVAL
from app.core.context import RequestContext
from app.core.langfuse_client import end_trace, flush_langfuse, langfuse_event, start_trace
from app.core.monitor import AgentMonitor
from app.services.chat_session import ChatSession
from app.services.session_service import (
    register_connection, unregister_connection, refresh_connection,
    wait_for_lock, release_lock,
)

logger = logging.getLogger(__name__)
_PROCESSED_MSG_IDS: set[str] = set()


class ChatSessionOrchestrator:

    def __init__(self, websocket: WebSocket, ctx: RequestContext, conn_id: str) -> None:
        self._ws = websocket
        self.ctx = ctx
        self._conn_id = conn_id
        self._monitor = AgentMonitor(websocket)
        self._heartbeat_task: asyncio.Task | None = None
        self._closed: bool = False
        self._trace_started: bool = False
        ctx.activate()
        self._session = ChatSession(ctx, self._monitor)

    async def run(self) -> None:
        try:
            await self.ctx.init_tenant_db()
            await self._message_loop()
        except (WebSocketDisconnect, RuntimeError):
            logger.info("WS disconnected: %s", self._conn_id)
        except Exception as e:
            logger.exception("WS error: %s", self._conn_id)
            try:
                await self._monitor.send_error(StatusCode.SERVER_ERROR, str(e))
            except Exception:
                pass
        finally:
            await self._cleanup()

    async def _cleanup(self) -> None:
        if self._trace_started:
            end_trace()
            flush_langfuse()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        if self.ctx.thread_id:
            await release_lock(self.ctx)
            await unregister_connection(self.ctx)
            remove_agent(self.ctx.thread_id)
        await self.ctx.close()

    async def _start_heartbeat(self) -> None:
        async def _beat():
            while True:
                await asyncio.sleep(WS_HEARTBEAT_INTERVAL)
                if self.ctx.thread_id:
                    await refresh_connection(self.ctx, self._conn_id)
                await self._monitor.send_heartbeat()
        self._heartbeat_task = asyncio.create_task(_beat())

    async def _message_loop(self) -> None:
        while not self._closed:
            raw = await self._ws.receive_text()
            msg = self._parse(raw)
            if msg is None:
                continue
            if self._is_duplicate(msg):
                continue
            await self._route(msg)

    def _parse(self, raw: str) -> dict | None:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            asyncio.create_task(self._monitor.send_error(StatusCode.BAD_REQUEST, "消息格式错误"))
            return None

    @staticmethod
    def _is_duplicate(msg: dict) -> bool:
        msg_id = msg.get("msg_id", "")
        if msg_id and msg_id in _PROCESSED_MSG_IDS:
            return True
        if msg_id:
            _PROCESSED_MSG_IDS.add(msg_id)
        return False

    async def _route(self, msg: dict) -> None:
        msg_type = msg.get("type", "")
        handler = getattr(self, f"_handle_{msg_type}", None)
        if handler:
            await handler(msg)
        else:
            logger.warning("Unknown WS message type: %s", msg_type)

    async def _handle_chat(self, msg: dict) -> None:
        thread_id = msg.get("thread_id")
        import_product_id = msg.get("import_product_id")
        if not thread_id or not import_product_id:
            await self._monitor.send_error(StatusCode.BAD_REQUEST, "缺少必填参数")
            return
        self.ctx.thread_id = thread_id
        self.ctx.import_product_id = import_product_id

        # 首次 chat 消息创建 LangFuse trace（一个连接一个 trace）
        if not self._trace_started:
            start_trace(
                name=f"chat_{thread_id}", user_id=self.ctx.user_id,
                session_id=thread_id, trace_id=import_product_id,
            )
            self._trace_started = True
            langfuse_event(self.ctx.langfuse_trace_id, "user_connected", metadata={
                "thread_id": thread_id, "import_product_id": import_product_id,
            })

        if not await register_connection(self.ctx, self._conn_id):
            await self._monitor.send_error(StatusCode.SESSION_CONFLICT, "该商品已有其他连接")
            await self._ws.close(code=4009)
            self._closed = True
            return

        if self._heartbeat_task is None:
            await self._start_heartbeat()

        if not await wait_for_lock(self.ctx):
            await self._monitor.send_error(StatusCode.SESSION_BUSY, "当前会话流程繁忙")
            return

        try:
            await self._session.handle_chat(
                operate_type=msg.get("operate_type", _O.BOTH),
                target_attrs=msg.get("target_attrs", []),
                user_content=msg.get("user_content", ""),
                manual_data=msg.get("manual_data"),
            )
        finally:
            await release_lock(self.ctx)

    async def _handle_confirm_reply(self, msg: dict) -> None:
        await self._session.handle_confirm(
            msg.get("operate_result", "cancel"), payload=msg.get("payload"))
