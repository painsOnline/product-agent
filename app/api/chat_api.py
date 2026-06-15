"""
文件名称：chat_api.py
作者：shop-tool
时间：2026-06-16
逻辑说明：WebSocket 聊天接口 + 历史记录 REST 接口.
"""
import logging
import uuid

from fastapi import APIRouter, Depends, Query, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.conf.constants import StatusCode
from app.core.context import RequestContext
from app.services.auth_service import authenticate, AuthError
from app.services.chat_history_service import load_chat_history
from app.services.chat_orchestrator import ChatSessionOrchestrator
from app.utils.response_utils import error, success

logger = logging.getLogger(__name__)

router = APIRouter(tags=["LLM 聊天"])


@router.get(
    "/chat/history",
    summary="获取聊天历史记录",
    description="首次打开聊天窗口时调用，获取当前商品的全部历史对话",
)
async def get_chat_history(
    thread_id: str = Query(..., description="会话ID（user_id_import_product_id）"),
    import_product_id: str = Query(..., description="导入商品ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取聊天历史."""
    try:
        ctx = RequestContext(
            tenant_code=user["tenant_code"],
            user_id=user["user_id"],
        )
        ctx.thread_id = thread_id
        ctx.import_product_id = import_product_id
        ctx.activate()
        await ctx.init_tenant_db()

        messages = await load_chat_history(ctx)
        await ctx.close()
        return success({"messages": messages})
    except Exception as e:
        logger.exception("Failed to load chat history")
        return error(code=StatusCode.SERVER_ERROR, msg=str(e))


@router.websocket("/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    """LLM 实时对话 WebSocket."""
    conn_id = str(uuid.uuid4())

    try:
        tenant_code = (
            websocket.headers.get("tenant", "")
            or websocket.query_params.get("tenant", "")
        )
        auth_header = websocket.headers.get("authorization", "")
        if not auth_header:
            token = websocket.query_params.get("token", "")
            if token:
                auth_header = f"Bearer {token}"
        user_info = await authenticate(auth_header, tenant_code)
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
