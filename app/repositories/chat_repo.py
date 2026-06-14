"""
文件名称：chat_repo.py
作者：shop-tool
时间：2026-06-14
逻辑说明：会话记录仓储，封装 t_chat_messages 表的 CRUD 操作.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage

logger = logging.getLogger(__name__)


async def create_message(
    db: AsyncSession,
    user_id: uuid.UUID,
    import_product_id: uuid.UUID,
    role: str,
    content: dict,
) -> ChatMessage:
    """创建会话消息."""
    msg = ChatMessage(
        user_id=user_id,
        import_product_id=import_product_id,
        role=role,
        content=content,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


async def get_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    import_product_id: uuid.UUID,
    limit: int = 50,
) -> list[ChatMessage]:
    """获取会话历史消息."""
    stmt = (
        select(ChatMessage)
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.import_product_id == import_product_id,
        )
        .order_by(ChatMessage.create_time.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_messages_by_thread(
    db: AsyncSession,
    user_id: uuid.UUID,
    import_product_id: uuid.UUID,
) -> list[ChatMessage]:
    """根据 thread 信息获取全量历史消息."""
    return await get_history(db, user_id, import_product_id, limit=200)
