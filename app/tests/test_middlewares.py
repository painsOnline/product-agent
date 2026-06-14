"""
文件名称：test_middlewares.py
作者：shop-tool
时间：2026-06-14
逻辑说明：Middleware 自动发现和基类单元测试.
"""
import pytest
from langchain_core.callbacks.base import BaseCallbackHandler

from app.middlewares import discover_middlewares
from app.middlewares.base import BaseMiddleware
from app.middlewares.logging import LoggingMiddleware


class TestBaseMiddleware:
    """BaseMiddleware 基类."""

    def test_is_callback_handler(self) -> None:
        m = BaseMiddleware()
        assert isinstance(m, BaseCallbackHandler)

    def test_enabled_by_default(self) -> None:
        m = BaseMiddleware()
        assert m.enabled is True


class TestLoggingMiddleware:
    """LoggingMiddleware 测试."""

    def test_instantiate(self) -> None:
        m = LoggingMiddleware()
        assert isinstance(m, BaseMiddleware)
        assert m.enabled is True


class TestDiscoverMiddlewares:
    """自动发现中间件."""

    def test_discovers_logging_middleware(self) -> None:
        mws = discover_middlewares()
        assert len(mws) >= 1
        names = {type(m).__name__ for m in mws}
        assert "LoggingMiddleware" in names

    def test_all_are_base_middleware(self) -> None:
        for m in discover_middlewares():
            assert isinstance(m, BaseMiddleware)
