"""
文件名称：product_repo.py
作者：shop-tool
时间：2026-06-14
逻辑说明：商品数据仓储，封装 t_ext_product_import_log 表的 CRUD 操作.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ext_product import ExtProductImportLog

logger = logging.getLogger(__name__)


async def get_by_ext_product_id(
    db: AsyncSession,
    ext_from: str,
    ext_product_id: str,
) -> ExtProductImportLog | None:
    """根据平台类型和第三方商品ID查询商品."""
    stmt = select(ExtProductImportLog).where(
        ExtProductImportLog.ext_from == ext_from,
        ExtProductImportLog.ext_product_id == ext_product_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_id(
    db: AsyncSession,
    product_id: uuid.UUID,
) -> ExtProductImportLog | None:
    """根据主键ID查询商品."""
    stmt = select(ExtProductImportLog).where(
        ExtProductImportLog.id == product_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_product(
    db: AsyncSession,
    ext_from: str,
    ext_product_id: str,
    ext_product_name: str,
    main_picture: str,
    pictures: list[str],
    detail_pictures: list[str],
    attrs: dict,
) -> ExtProductImportLog:
    """创建商品记录."""
    product = ExtProductImportLog(
        ext_from=ext_from,
        ext_product_id=ext_product_id,
        ext_product_name=ext_product_name,
        main_picture=main_picture,
        pictures=pictures,
        detail_pictures=detail_pictures,
        attrs=attrs,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    logger.info(
        "Created product record: %s from %s/%s",
        product.id,
        ext_from,
        ext_product_id,
    )
    return product


async def update_product(
    db: AsyncSession,
    product: ExtProductImportLog,
    **kwargs,
) -> ExtProductImportLog:
    """更新商品记录."""
    for key, value in kwargs.items():
        if hasattr(product, key):
            setattr(product, key, value)
    await db.flush()
    await db.refresh(product)
    return product


async def list_products(
    db: AsyncSession,
    ext_from: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[ExtProductImportLog], int]:
    """分页查询商品列表."""
    from sqlalchemy import func as sql_func

    stmt = select(ExtProductImportLog)
    count_stmt = select(sql_func.count()).select_from(ExtProductImportLog)

    if ext_from:
        stmt = stmt.where(ExtProductImportLog.ext_from == ext_from)
        count_stmt = count_stmt.where(ExtProductImportLog.ext_from == ext_from)

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = stmt.order_by(ExtProductImportLog.create_time.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return items, total
