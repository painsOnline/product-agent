"""
文件名称：image_downloader.py
作者：shop-tool
时间：2026-06-14
逻辑说明：图片下载与校验工具，处理 HTTP 下载、超时重试、无效图片过滤.

从 image_service.py 中提取，遵循 SRP：下载/校验与文件系统存储分离.
"""
import logging
from io import BytesIO

import httpx
from PIL import Image

from app.conf.constants import IMAGE_DOWNLOAD_RETRIES, IMAGE_DOWNLOAD_TIMEOUT
from app.utils.video_detector import is_video_url

logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE = 10 * 1024 * 1024


def validate_image(data: bytes) -> bool:
    """验证图片是否有效（非空白、非 1x1 占位图）."""
    try:
        img = Image.open(BytesIO(data))
        width, height = img.size
        if width <= 1 or height <= 1:
            logger.warning("Rejected invalid image: %dx%d", width, height)
            return False
        if data and len(data) < 100:
            logger.warning("Rejected too small image: %d bytes", len(data))
            return False
        return True
    except Exception:
        logger.warning("Failed to parse image data, rejecting")
        return False


async def download_image(url: str) -> bytes | None:
    """下载单张图片，10s 超时，失败重试 1 次.

    Returns:
        图片字节数据，失败返回 None
    """
    if not url or not url.startswith("http"):
        logger.warning("Invalid image URL: %s", url)
        return None

    if is_video_url(url):
        logger.warning("Skipping video URL: %s", url)
        return None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        ),
        "Referer": "https://detail.1688.com/",
    }

    for attempt in range(IMAGE_DOWNLOAD_RETRIES + 1):
        try:
            async with httpx.AsyncClient(
                timeout=IMAGE_DOWNLOAD_TIMEOUT,
                follow_redirects=True,
            ) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.content
                if len(data) > MAX_IMAGE_SIZE:
                    logger.warning(
                        "Image too large: %s (%d bytes)", url, len(data)
                    )
                    return None
                if not validate_image(data):
                    return None
                return data
        except httpx.TimeoutException:
            logger.warning(
                "Download timeout for %s (attempt %d)", url, attempt + 1
            )
        except Exception as e:
            logger.warning(
                "Download failed for %s (attempt %d): %s", url, attempt + 1, e
            )

    return None
