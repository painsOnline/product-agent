"""
文件名称：langfuse_client.py
作者：shop-tool
时间：2026-06-21
逻辑说明：LangFuse 客户端封装，模块导入时自动初始化，所有异常隔离.
"""
import hashlib
import logging
from contextlib import contextmanager, nullcontext
from typing import Any

from app.conf.settings import get_settings

logger = logging.getLogger(__name__)

_langfuse_client: Any = None


def _do_init() -> Any | None:
    """模块导入时尝试初始化 LangFuse 客户端."""
    global _langfuse_client
    settings = get_settings()
    if not settings.langfuse_enabled:
        logger.info("LangFuse disabled by config")
        return None
    try:
        from langfuse import Langfuse as LF
        client = LF(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_base_url,
        )
        logger.info("LangFuse initialized: %s", settings.langfuse_base_url)
        _langfuse_client = client
        return client
    except ImportError:
        logger.warning("langfuse package not installed")
        return None
    except Exception as e:
        logger.warning("LangFuse init failed: %s", e)
        return None


def init_langfuse() -> None:
    """初始化 LangFuse 客户端。幂等 — 重复调用无副作用."""
    global _langfuse_client
    print("[LangFuse DEBUG] init_langfuse() called, current client:", _langfuse_client)
    if _langfuse_client is not None:
        print("[LangFuse DEBUG] Already initialized, skipping")
        return
    settings = get_settings()
    print(f"[LangFuse DEBUG] enabled={settings.langfuse_enabled}, url={settings.langfuse_base_url}")
    if not settings.langfuse_enabled:
        logger.info("LangFuse disabled by config")
        return
    try:
        from langfuse import Langfuse as LF
        _langfuse_client = LF(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_base_url,
        )
        logger.info("LangFuse initialized: %s", settings.langfuse_base_url)
        print("[LangFuse DEBUG] Init SUCCESS")
    except ImportError:
        logger.warning("langfuse package not installed")
        print("[LangFuse DEBUG] FAILED: langfuse not installed")
    except Exception as e:
        logger.warning("LangFuse init failed: %s", e)
        print(f"[LangFuse DEBUG] FAILED: {e}")
        _langfuse_client = None


def get_langfuse() -> Any | None:
    init_langfuse()
    print("[LangFuse DEBUG] get_langfuse() ->", _langfuse_client is not None)
    return _langfuse_client


def get_trace_id() -> str:
    try:
        from app.core.context import RequestContext
        ctx = RequestContext.current()
        return ctx.langfuse_trace_id if ctx else ""
    except Exception:
        return ""


# ── Trace ──────────────────────────────────────

def _to_trace_id(raw: str) -> str | None:
    """将任意字符串转为合法 32 位 hex trace_id."""
    if not raw:
        return None
    if len(raw) == 32 and all(c in "0123456789abcdef" for c in raw.lower()):
        return raw
    return hashlib.md5(raw.encode()).hexdigest()


@contextmanager
def langfuse_trace(name, user_id, session_id, trace_id="", input_data=None, metadata=None):
    """创建 LangFuse Trace 上下文管理器（用于 auto_match 等同步流程）."""
    lf = get_langfuse()
    print(f"[LangFuse DEBUG] langfuse_trace() lf={lf is not None}, name={name}, session_id={session_id}, trace_id={trace_id}")
    if lf is None:
        print("[LangFuse DEBUG] langfuse_trace() NO CLIENT - yielding without trace")
        yield
        return

    ctx = None
    try:
        from app.core.context import RequestContext
        ctx = RequestContext.current()
    except Exception:
        pass
    print(f"[LangFuse DEBUG] langfuse_trace() ctx={ctx is not None}, thread_id={ctx.thread_id if ctx else 'N/A'}")

    tc = {"trace_id": _to_trace_id(trace_id)} if _to_trace_id(trace_id) else None
    print(f"[LangFuse DEBUG] langfuse_trace() trace_context={tc}")
    try:
        with lf.start_as_current_observation(
            name=name, input=input_data, metadata=metadata, as_type="span", trace_context=tc,
        ) as span:
            print(f"[LangFuse DEBUG] langfuse_trace() span created, trace_id={lf.get_current_trace_id()}")
            if ctx:
                ctx.langfuse_trace_id = lf.get_current_trace_id() or ""
                ctx._langfuse_trace_span = span
            # 设置 session / user
            if session_id or user_id:
                try:
                    import opentelemetry.trace as otel_trace
                    s = otel_trace.get_current_span()
                    if s and s.is_recording():
                        if session_id:
                            s.set_attribute("session.id", session_id)
                        if user_id:
                            s.set_attribute("user.id", user_id)
                except Exception:
                    pass
            yield span
    except Exception as e:
        logger.warning("LangFuse trace failed: %s", e)
        yield


# ── Span ───────────────────────────────────────

@contextmanager
def langfuse_span(name, input_data=None):
    """创建子 Span 上下文管理器（用于节点内）."""
    lf = get_langfuse()
    tid = get_trace_id()
    print(f"[LangFuse DEBUG] langfuse_span({name}) lf={lf is not None}, tid={tid[:16] if tid else 'EMPTY'}")
    if lf is None or not tid:
        print(f"[LangFuse DEBUG] langfuse_span({name}) NO CLIENT/TRACE - yielding None")
        yield None
        return

    try:
        with lf.start_as_current_observation(
            trace_context={"trace_id": tid}, name=name, input=input_data, as_type="span",
        ) as span:
            print(f"[LangFuse DEBUG] langfuse_span({name}) span created, id={span.id}")
            # 显式传播 session / user
            try:
                from app.core.context import RequestContext
                ctx = RequestContext.current()
                if ctx and (ctx.thread_id or ctx.user_id):
                    import opentelemetry.trace as otel_trace
                    s = otel_trace.get_current_span()
                    if s and s.is_recording():
                        if ctx.thread_id:
                            s.set_attribute("session.id", ctx.thread_id)
                        if ctx.user_id:
                            s.set_attribute("user.id", ctx.user_id)
            except Exception:
                pass
            yield span
    except Exception as e:
        logger.warning("LangFuse span(%s) failed: %s", name, e)
        print(f"[LangFuse DEBUG] langfuse_span({name}) FAILED: {e}")
        yield


# ── CallbackHandler ────────────────────────────

def create_callback_handler() -> Any | None:
    lf = get_langfuse()
    tid = get_trace_id()
    print(f"[LangFuse DEBUG] create_callback_handler() lf={lf is not None}, tid={tid[:16] if tid else 'EMPTY'}")
    if lf is None or not tid:
        print("[LangFuse DEBUG] create_callback_handler() NO CLIENT/TRACE - returning None")
        return None
    try:
        from langfuse.langchain import CallbackHandler  # type: ignore[import-untyped]
        handler = CallbackHandler()
        print(f"[LangFuse DEBUG] create_callback_handler() SUCCESS")
        return handler
    except Exception as e:
        logger.warning("LangFuse CallbackHandler creation failed: %s", e)
        print(f"[LangFuse DEBUG] create_callback_handler() FAILED: {e}")
        return None


def inject_callback(config: dict, handler: Any) -> dict:
    if handler is None:
        return dict(config)
    existing = config.get("callbacks")
    if existing is None:
        return {**config, "callbacks": [handler]}
    if isinstance(existing, list):
        return {**config, "callbacks": existing + [handler]}
    try:
        existing.add_handler(handler)
    except Exception:
        pass
    return {**config}


# ── Event ──────────────────────────────────────

def langfuse_event(trace_id: str, name: str, metadata: dict | None = None, level: str | None = None):
    lf = get_langfuse()
    if lf is None or not trace_id:
        return
    try:
        lf.create_event(trace_context={"trace_id": trace_id}, name=name, metadata=metadata, level=level)
    except Exception as e:
        logger.warning("LangFuse event(%s) failed: %s", name, e)


# ── Manual Trace（用于跨函数生命周期的场景，如 WebSocket 连接）──

def start_trace(name, user_id, session_id, trace_id="", input_data=None, metadata=None):
    """手动创建 Trace（start / end 配对，用于跨方法场景）.
    返回 (span, attr_ctx)，调用方在结束时应调用 end_trace().
    """
    lf = get_langfuse()
    if lf is None:
        return None, None, None

    from app.core.context import RequestContext
    ctx = RequestContext.current()

    tc = {"trace_id": _to_trace_id(trace_id)} if _to_trace_id(trace_id) else None
    try:
        span_ctx = lf.start_as_current_observation(
            name=name, input=input_data, metadata=metadata,
            as_type="span", trace_context=tc,
        )
        span = span_ctx.__enter__()

        if session_id or user_id:
            try:
                import opentelemetry.trace as otel_trace
                s = otel_trace.get_current_span()
                if s and s.is_recording():
                    if session_id:
                        s.set_attribute("session.id", session_id)
                    if user_id:
                        s.set_attribute("user.id", user_id)
            except Exception:
                pass

        from langfuse import propagate_attributes
        attr_ctx = propagate_attributes(session_id=session_id, user_id=user_id)
        attr_ctx.__enter__()

        if ctx and span:
            ctx.langfuse_trace_id = lf.get_current_trace_id() or ""
            ctx._langfuse_trace_ctx = span_ctx
            ctx._langfuse_attr_ctx = attr_ctx

        return span, attr_ctx, span_ctx
    except Exception as e:
        logger.warning("LangFuse start_trace failed: %s", e)
        return None, None, None


def end_trace():
    """结束当前手动创建的 trace."""
    try:
        from app.core.context import RequestContext
        ctx = RequestContext.current()
        if ctx:
            for c in (ctx._langfuse_attr_ctx, ctx._langfuse_trace_ctx):
                if c is not None:
                    try:
                        c.__exit__(None, None, None)
                    except Exception:
                        pass
            ctx._langfuse_trace_ctx = None
            ctx._langfuse_attr_ctx = None
    except Exception:
        pass


# ── Lifecycle ──────────────────────────────────

def flush_langfuse():
    lf = get_langfuse()
    if lf:
        try:
            print("[LangFuse DEBUG] flush_langfuse() called")
            lf.flush()
            print("[LangFuse DEBUG] flush_langfuse() done")
        except Exception as e:
            logger.warning("LangFuse flush failed: %s", e)
            print(f"[LangFuse DEBUG] flush FAILED: {e}")


def shutdown_langfuse():
    global _langfuse_client
    lf = _langfuse_client
    if lf:
        try:
            lf.flush()
            lf.shutdown()
        except Exception as e:
            logger.warning("LangFuse shutdown failed: %s", e)
    _langfuse_client = None
