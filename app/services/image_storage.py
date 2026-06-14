"""
文件名称：image_storage.py
作者：shop-tool
时间：2026-06-14
逻辑说明：图片文件系统存储工具，处理路径构造、文件名安全清洗、目录创建、文件写入.

从 image_service.py 中提取，遵循 SRP：存储路径与下载/校验分离.
"""
import logging
import os
import urllib.parse
from pathlib import Path

from app.conf.settings import get_settings
from app.utils.video_detector import is_video_url

logger = logging.getLogger(__name__)

settings = get_settings()


def get_product_dir(
    tenant_code: str,
    ext_from: str,
    ext_product_id: str,
) -> Path:
    """获取商品图片存储根目录."""
    base = Path(settings.upload_path)
    return base / tenant_code / "agents" / "product" / ext_from / ext_product_id


def sanitize_filename(url: str) -> str:
    """从 URL 提取并净化文件名."""
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path)
    name = os.path.basename(path)
    if not name or "." not in name:
        name = "image.jpg"
    safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    clean = "".join(c if c in safe_chars else "_" for c in name)
    return clean


def get_extension(url: str, default_ext: str = ".jpg") -> str:
    """从 URL 获取文件扩展名."""
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path)
    _, ext = os.path.splitext(path)
    if ext and len(ext) <= 5:
        return ext.lower()
    return default_ext


def get_failure_reason(url: str) -> str:
    """获取图片下载失败的具体原因."""
    if not url or not url.startswith("http"):
        return "无效的图片URL"
    if is_video_url(url):
        return "视频文件已过滤"
    return "下载超时或图片无效"


def write_image(
    tenant_code: str,
    ext_from: str,
    ext_product_id: str,
    filename: str,
    data: bytes,
    sub_dir: str | None = None,
) -> str:
    """写入图片到本地文件系统，返回服务器相对路径.

    Args:
        tenant_code: 租户 code
        ext_from: 平台类型（1688/taobao）
        ext_product_id: 第三方商品 ID
        filename: 文件名（含扩展名）
        data: 图片字节数据
        sub_dir: 子目录名，None 表示根目录

    Returns:
        服务器相对路径，如 /uploads/xxx/main.jpg
    """
    product_dir = get_product_dir(tenant_code, ext_from, ext_product_id)
    target_dir = product_dir / sub_dir if sub_dir else product_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    filepath = target_dir / filename
    filepath.write_bytes(data)
    relative_path = str(filepath.relative_to(Path(settings.upload_path)))
    relative_path = relative_path.replace("\\", "/")
    return f"/uploads/{relative_path}"
