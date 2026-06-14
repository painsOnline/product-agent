"""
文件名称：tenant.py
作者：shop-tool
时间：2026-06-14
逻辑说明：租户表 ORM 模型（mypet_config 配置库）.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Tenant(Base):
    """租户表 (mypet_config 库)."""

    __tablename__ = "c_tenant"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    database_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    free_shipping_amount: Mapped[float] = mapped_column(
        Numeric(8, 2), nullable=False, default=20.00
    )
    is_disable: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    is_bussiness_open: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
    modify_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
