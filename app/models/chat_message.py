"""
文件名称：chat_message.py
作者：shop-tool
时间：2026-06-14
逻辑说明：LLM 会话记录表 ORM 模型，对应 t_chat_messages 表.
"""
import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ChatMessage(Base):
    """LLM 会话记录表."""

    __tablename__ = "t_chat_messages"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    import_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
