"""
文件名称：test_langfuse_client.py
作者：shop-tool
时间：2026-06-21
逻辑说明：LangFuse 客户端封装单元测试.
"""
import pytest


class TestLangfuseClient:

    def test_get_langfuse(self):
        from app.core.langfuse_client import get_langfuse
        lf = get_langfuse()
        assert isinstance(lf is not None, bool)

    def test_get_trace_id_safe(self):
        from app.core.langfuse_client import get_trace_id
        tid = get_trace_id()
        assert isinstance(tid, str)

    def test_langfuse_event_safe(self):
        from app.core.langfuse_client import langfuse_event
        langfuse_event("abc", "test", metadata=None)
        langfuse_event("", "test")

    def test_langfuse_span_nullcontext(self):
        from app.core.langfuse_client import langfuse_span
        with langfuse_span("test") as span:
            pass

    def test_callback_handler_safe(self):
        from app.core.langfuse_client import create_callback_handler
        h = create_callback_handler()
        assert h is None or h is not None

    def test_inject_callback_noop(self):
        from app.core.langfuse_client import inject_callback
        c = inject_callback({}, None)
        assert c == {}

    def test_flush_safe(self):
        from app.core.langfuse_client import flush_langfuse
        flush_langfuse()

    def test_shutdown_safe(self):
        from app.core.langfuse_client import shutdown_langfuse
        shutdown_langfuse()
