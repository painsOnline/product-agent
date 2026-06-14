"""
文件名称：product_service.py
作者：shop-tool
时间：2026-06-14
逻辑说明：商品服务，协调图片下载和数据库操作.

保存流程：
1. 下载主图 → 存储路径
2. 批量下载轮播图 → 存储路径
3. 批量下载详情图 → 存储路径
4. 将所有路径写入数据库
5. 构建响应 DTO
"""
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.product import ProductData
from app.repositories import product_repo
from app.repositories.protocols import ProductRepository
from app.services import image_service
from app.services.product_dto import build_save_response

logger = logging.getLogger(__name__)


async def save_product(
    db: AsyncSession,
    tenant_code: str,
    ext_from: str,
    ext_product_id: str,
    ext_product_name: str,
    main_picture_url: str,
    pictures_urls: list[str],
    detail_pictures_urls: list[str],
    attrs: dict[str, str],
    *,
    repo: ProductRepository = product_repo,
):
    """保存商品数据，包含图片下载."""
    existing = await repo.get_by_ext_product_id(
        db, ext_from, ext_product_id
    )
    if existing:
        logger.info(
            "Product already exists: %s/%s, updating", ext_from, ext_product_id
        )

    main_result = await image_service.download_main_image(
        tenant_code, ext_from, ext_product_id, main_picture_url
    )

    slides_success, slides_fail = await image_service.download_slides(
        tenant_code, ext_from, ext_product_id, pictures_urls
    )

    details_success, details_fail = await image_service.download_details(
        tenant_code, ext_from, ext_product_id, detail_pictures_urls
    )

    main_path = main_result[0] if main_result else ""
    slide_paths = [s["image_path"] for s in slides_success]
    detail_paths = [d["image_path"] for d in details_success]

    if existing:
        product = await repo.update_product(
            db,
            existing,
            ext_product_name=ext_product_name,
            main_picture=main_path,
            pictures=slide_paths,
            detail_pictures=detail_paths,
            attrs=attrs,
            modify_time=datetime.now(),
        )
    else:
        product = await repo.create_product(
            db=db,
            ext_from=ext_from,
            ext_product_id=ext_product_id,
            ext_product_name=ext_product_name,
            main_picture=main_path,
            pictures=slide_paths,
            detail_pictures=detail_paths,
            attrs=attrs,
        )

    return build_save_response(
        product, slides_success, slides_fail, details_success, details_fail
    )


async def get_product(
    db: AsyncSession,
    ext_from: str,
    ext_product_id: str,
    *,
    repo: ProductRepository = product_repo,
) -> ProductData | None:
    """根据平台和商品ID查询商品数据."""
    product = await repo.get_by_ext_product_id(db, ext_from, ext_product_id)
    if not product:
        return None

    return ProductData(
        id=str(product.id),
        ext_from=product.ext_from,
        ext_product_id=product.ext_product_id,
        ext_product_name=product.ext_product_name,
        main_picture=product.main_picture,
        pictures=product.pictures or [],
        detail_pictures=product.detail_pictures or [],
        attrs=product.attrs or {},
    )
