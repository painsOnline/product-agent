"""
文件名称：ext_product.py
作者：shop-tool
时间：2026-06-14
逻辑说明：第三方导入商品记录表 ORM 模型，对应 t_ext_product_import_log 表.
"""
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ExtProductImportLog(Base):
    """第三方导入商品记录表."""

    __tablename__ = "t_ext_product_import_log"

    ext_from: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )
    ext_product_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    ext_product_name: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True
    )
    main_picture: Mapped[str] = mapped_column(String(500), nullable=False)
    pictures: Mapped[list] = mapped_column(ARRAY(String(500)), nullable=False)
    detail_pictures: Mapped[list | None] = mapped_column(
        ARRAY(String(500)), nullable=True
    )
    attrs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
