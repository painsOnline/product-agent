"""
文件名称：base.py
作者：shop-tool
时间：2026-06-14
逻辑说明：SQLAlchemy ORM 基类，提供公共字段 id、create_time、modify_time.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """ORM 基类."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
    modify_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )
