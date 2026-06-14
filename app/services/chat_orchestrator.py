"""
文件名称：chat_orchestrator.py
作者：shop-tool
时间：2026-06-14
逻辑说明：WebSocket 连接生命周期管理，所有参数通过 RequestContext 传递.
"""
import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.agent.main_agent import remove_agent
from app.conf.constants import StatusCode, WS_HEARTBEAT_INTERVAL
from app.core.context import RequestContext
from app.core.monitor import AgentMonitor
from app.services.chat_session import ChatSession
from app.services.session_service import (
    register_connection,
    unregister_connection,
    refresh_connection,
    wait_for_lock,
    release_lock,
)

logger = logging.getLogger(__name__)

_PROCESSED_MSG_IDS: set[str] = set()


class ChatSessionOrchestrator:
    """WebSocket 连接管理器."""

    def __init__(self, websocket: WebSocket, ctx: RequestContext, conn_id: str) -> None:
        self._ws = websocket
        self.ctx = ctx
        self._conn_id = conn_id
        self._monitor = AgentMonitor(websocket)
        self._heartbeat_task: asyncio.Task | None = None
        ctx.activate()
        self._session = ChatSession(ctx, self._monitor)

    async def run(self) -> None:
        try:
            await self.ctx.init_tenant_db()
            await self._message_loop()
        except WebSocketDisconnect:
            logger.info("WS disconnected: %s", self._conn_id)
        except Exception as e:
            logger.exception("WS error: %s", self._conn_id)
            try:
                await self._monitor.send_error(StatusCode.SERVER_ERROR, str(e))
            except Exception:
                pass
        finally:
            await self._cleanup()

    async def _start_heartbeat(self) -> None:
        async def _beat():
            while True:
                await asyncio.sleep(WS_HEARTBEAT_INTERVAL)
                if self.ctx.thread_id:
                    await refresh_connection(self.ctx, self._conn_id)
                await self._monitor.send_heartbeat()
        self._heartbeat_task = asyncio.create_task(_beat())

    async def _cleanup(self) -> None:
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

    async def _message_loop(self) -> None:
        while True:
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
        self.ctx.thread_id = msg.get("thread_id", "")
        self.ctx.import_product_id = msg.get("import_product_id", "")

        if not await register_connection(self.ctx, self._conn_id):
            await self._monitor.send_error(StatusCode.SESSION_CONFLICT, "该商品已有其他连接")
            await self._ws.close(code=4009)
            return

        if self._heartbeat_task is None:
            await self._start_heartbeat()

        if not await wait_for_lock(self.ctx):
            await self._monitor.send_error(StatusCode.SESSION_BUSY, "当前会话流程繁忙")
            return

        try:
            await self._session.handle_chat(
                operate_type=msg.get("operate_type", "both"),
                origin_title=msg.get("origin_title", ""),
                origin_attrs=msg.get("origin_attrs", []),
                user_content=msg.get("user_content", ""),
            )
        finally:
            await release_lock(self.ctx)

    async def _handle_confirm_reply(self, msg: dict) -> None:
        await self._session.handle_confirm(msg.get("operate_result", "cancel"))
