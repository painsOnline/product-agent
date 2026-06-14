"""
文件名称：database_instance.py
作者：shop-tool
时间：2026-06-14
逻辑说明：租户数据库实例表 ORM 模型（mypet_config 配置库）.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DatabaseInstance(Base):
    """数据库实例表 (mypet_config 库)."""

    __tablename__ = "c_database_instance"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    user: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
    modify_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
