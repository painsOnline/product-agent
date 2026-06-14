"""
文件名称：image_utils.py
作者：shop-tool
时间：2026-06-14
逻辑说明：图片工具函数，URL 校验、文件扩展名检测、文件名净化.
"""
import os
import urllib.parse


def get_extension_from_url(url: str, default_ext: str = ".jpg") -> str:
    """从 URL 获取文件扩展名."""
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path)
    _, ext = os.path.splitext(path)
    if ext and len(ext) <= 5 and ext.isascii():
        return ext.lower()
    return default_ext


def sanitize_filename(name: str) -> str:
    """净化文件名，移除特殊字符和中文."""
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    return "".join(c if c in safe else "_" for c in name)


def is_valid_image_url(url: str) -> bool:
    """检查是否为有效的图片 URL."""
    if not url or not url.startswith(("http://", "https://")):
        return False
    valid_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path).lower()
    return any(path.endswith(ext) for ext in valid_extensions) or "img" in url.lower()
