"""
文件名称：image_service.py
作者：shop-tool
时间：2026-06-14
逻辑说明：图片服务薄门面，汇聚下载、校验、存储、视频检测模块的公开 API.

职责拆分（SRP）：
- image_downloader.py: 图片下载 + 校验（download_image, validate_image）
- image_storage.py: 文件系统路径 + 写入（write_image, sanitize_filename, get_extension）
- utils/video_detector.py: 视频 URL 检测（is_video_url）
"""
import asyncio
import logging
import random

from app.conf.constants import IMAGE_DOWNLOAD_DELAY_MAX, IMAGE_DOWNLOAD_DELAY_MIN
from app.conf.settings import get_settings
from app.services.image_downloader import download_image
from app.services.image_storage import (
    get_extension,
    get_failure_reason,
    get_product_dir,
    sanitize_filename,
    write_image,
)

logger = logging.getLogger(__name__)

settings = get_settings()


async def download_main_image(
    tenant_code: str,
    ext_from: str,
    ext_product_id: str,
    image_url: str,
) -> tuple[str, int] | None:
    """下载主图，返回 (相对路径, 文件大小) 或 None."""
    data = await download_image(image_url)
    if not data:
        return None

    ext = get_extension(image_url)
    filename = f"main{ext}"
    path = write_image(tenant_code, ext_from, ext_product_id, filename, data)
    return path, len(data)


async def download_slides(
    tenant_code: str,
    ext_from: str,
    ext_product_id: str,
    image_urls: list[str],
) -> tuple[list[dict], list[dict]]:
    """下载轮播图."""
    return await _download_batch(
        tenant_code, ext_from, ext_product_id, image_urls, "pictures", "slide"
    )


async def download_details(
    tenant_code: str,
    ext_from: str,
    ext_product_id: str,
    image_urls: list[str],
) -> tuple[list[dict], list[dict]]:
    """下载详情图."""
    return await _download_batch(
        tenant_code, ext_from, ext_product_id, image_urls, "detail_pictures", "detail"
    )


async def _download_batch(
    tenant_code: str,
    ext_from: str,
    ext_product_id: str,
    image_urls: list[str],
    sub_dir: str,
    prefix: str,
) -> tuple[list[dict], list[dict]]:
    """批量下载图片到指定子目录."""
    success_list: list[dict] = []
    fail_list: list[dict] = []

    for idx, url in enumerate(image_urls):
        # 随机延迟，避免并发触发防盗链
        if idx > 0:
            delay = random.uniform(IMAGE_DOWNLOAD_DELAY_MIN, IMAGE_DOWNLOAD_DELAY_MAX)
            await asyncio.sleep(delay)

        data = await download_image(url)
        if not data:
            fail_list.append({
                "image_name": sanitize_filename(url),
                "reason": get_failure_reason(url),
            })
            continue

        ext = get_extension(url)
        filename = f"{prefix}_{idx + 1:02d}{ext}"
        path = write_image(tenant_code, ext_from, ext_product_id, filename, data, sub_dir)
        success_list.append({
            "image_path": path,
            "image_size": len(data),
        })

    return success_list, fail_list
