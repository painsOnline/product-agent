"""
文件名称：chat_api.py
作者：shop-tool
时间：2026-06-14
逻辑说明：WebSocket 聊天接口入口，鉴权后创建 RequestContext 委托给 ChatSessionOrchestrator.
"""
import logging
import uuid

from fastapi import APIRouter, WebSocket

from app.core.context import RequestContext
from app.services.auth_service import authenticate, AuthError
from app.services.chat_orchestrator import ChatSessionOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["LLM 聊天"])


@router.websocket("/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    """LLM 实时对话 WebSocket."""
    conn_id = str(uuid.uuid4())

    try:
        tenant_code = websocket.headers.get("tenant", "")
        authorization = websocket.headers.get("authorization", "")
        user_info = await authenticate(authorization, tenant_code)
    except AuthError as e:
        await websocket.close(code=4001, reason=e.msg)
        return

    await websocket.accept()
    logger.info("WS accepted: conn=%s user=%s", conn_id, user_info["user_id"])

    ctx = RequestContext(
        tenant_code=tenant_code,
        user_id=user_info["user_id"],
    )
    orchestrator = ChatSessionOrchestrator(websocket, ctx, conn_id)
    await orchestrator.run()
