"""
文件名称：response_utils.py
作者：shop-tool
时间：2026-06-14
逻辑说明：统一 API 响应构建工具函数.
"""
from typing import Any

from app.conf.constants import StatusCode


def success(
    result: Any = None,
    msg: str = "success",
) -> dict[str, Any]:
    """构建成功响应."""
    return {
        "code": StatusCode.SUCCESS,
        "msg": msg,
        "result": result,
    }


def error(
    code: str = StatusCode.SERVER_ERROR,
    msg: str = "error",
    result: Any = None,
) -> dict[str, Any]:
    """构建错误响应."""
    return {
        "code": code,
        "msg": msg,
        "result": result,
    }


def paginated(
    items: list,
    total: int,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """构建分页响应."""
    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "code": StatusCode.SUCCESS,
        "msg": "success",
        "result": {
            "items": items,
            "counts": total,
            "page": page,
            "pages": pages,
            "page_size": page_size,
        },
    }
