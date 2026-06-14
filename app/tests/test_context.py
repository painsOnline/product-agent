"""
文件名称：test_context.py
作者：shop-tool
时间：2026-06-14
逻辑说明：RequestContext 单元测试.
"""
import pytest

from app.core.context import RequestContext


class TestRequestContext:
    """RequestContext 功能测试."""

    def test_create_context(self) -> None:
        ctx = RequestContext(tenant_code="test", user_id="u1")
        assert ctx.tenant_code == "test"
        assert ctx.user_id == "u1"
        assert ctx.import_product_id == ""
        assert ctx.thread_id == ""

    def test_set_fields(self) -> None:
        ctx = RequestContext(tenant_code="test")
        ctx.thread_id = "t1"
        ctx.import_product_id = "p1"
        assert ctx.thread_id == "t1"
        assert ctx.import_product_id == "p1"

    def test_activate_and_current(self) -> None:
        ctx = RequestContext(tenant_code="test", user_id="u1")
        ctx.activate()
        assert RequestContext.current() is ctx
        # cleanup
        ctx2 = RequestContext(tenant_code="", user_id="")
        ctx2.activate()

    def test_tenant_db_not_init(self) -> None:
        ctx = RequestContext(tenant_code="test")
        assert ctx.tenant_db() is None

    def test_close_disconnects_resources(self) -> None:
        import asyncio
        ctx = RequestContext(tenant_code="test")
        ctx.activate()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(ctx.close())
        assert ctx._redis is None
        # re-activate empty to clean up
        clean = RequestContext(tenant_code="")
        clean.activate()
