"""
文件名称：video_detector.py
作者：shop-tool
时间：2026-06-14
逻辑说明：视频 URL 检测工具，识别视频文件和视频封面链接.

从 image_service.py 中提取，遵循 SRP：图片下载与视频检测分离.
"""
import os
import urllib.parse

# 视频文件扩展名
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m3u8"}

# URL 中常见的视频关键词
VIDEO_URL_KEYWORDS = ["video", "mp4", "m3u8", "play", "/v/"]


def is_video_url(url: str) -> bool:
    """检测 URL 是否为视频文件或视频封面.

    Args:
        url: 图片/视频 URL

    Returns:
        True 表示该 URL 是视频，应跳过下载
    """
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path).lower()
    _, ext = os.path.splitext(path)
    if ext in VIDEO_EXTENSIONS:
        return True
    for kw in VIDEO_URL_KEYWORDS:
        if kw in url.lower():
            return True
    return False
