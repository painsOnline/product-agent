"""
文件名称：common.py
作者：shop-tool
时间：2026-06-14
逻辑说明：通用 API 响应实体定义.
"""
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """统一 API 响应格式."""
    code: str = Field("200", description="状态码")
    msg: str = Field("success", description="返回信息")
    result: T | None = Field(None, description="业务数据")


class PaginatedResult(BaseModel, Generic[T]):
    """分页结果."""
    items: list[T] = Field(default_factory=list, description="数据列表")
    counts: int = Field(0, description="总记录数")
    page: int = Field(1, description="当前页")
    pages: int = Field(1, description="总页数")
    page_size: int = Field(10, description="每页记录数")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页 API 响应格式."""
    code: str = Field("200")
    msg: str = Field("success")
    result: PaginatedResult[T] = Field(default_factory=PaginatedResult)
