"""
文件名称：agent_action_log.py
作者：shop-tool
时间：2026-06-14
逻辑说明：LLM 操作日志表 ORM 模型，对应 t_agent_action_logs 表.
"""
import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentActionLog(Base):
    """LLM 操作日志表."""

    __tablename__ = "t_agent_action_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    import_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    request: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    extra: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )
