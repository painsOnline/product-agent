"""
文件名称：shop_llm_config.py
作者：shop-tool
时间：2026-06-14
逻辑说明：店铺大模型配置表 ORM 模型，对应 t_shop_llm_config 表.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ShopLLMConfig(Base):
    """店铺大模型配置表."""

    __tablename__ = "t_shop_llm_config"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    temperature: Mapped[float] = mapped_column(
        Numeric(3, 2), nullable=False, default=0.3
    )
    max_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=4096
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    max_retries: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
    modify_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
