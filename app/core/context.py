"""
文件名称：context.py
作者：shop-tool
时间：2026-06-15
逻辑说明：请求级上下文对象，每个请求一个实例，统一管理 Redis + PG 连接和用户身份.
"""
import contextvars
import logging
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.conf.database import ConfigSessionLocal, _get_tenant_engine
from app.conf.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_current: contextvars.ContextVar["RequestContext | None"] = (
    contextvars.ContextVar("request_ctx", default=None)
)


class RequestContext:
    """请求级全局上下文，管理连接和身份."""

    def __init__(
        self,
        tenant_code: str,
        user_id: str,
        import_product_id: str = "",
    ) -> None:
        if not tenant_code:
            raise ValueError("tenant_code is required")
        if not user_id:
            raise ValueError("user_id is required")
        self.tenant_code = tenant_code
        self.user_id = user_id
        self.import_product_id = import_product_id
        self.thread_id: str = ""

        # LangFuse trace context（生命周期 = WS 连接）
        self.langfuse_trace_id: str = ""
        self._langfuse_trace_ctx: Any = None
        self._langfuse_attr_ctx: Any = None
        self._langfuse_hitl_span: Any = None

        self._redis: Redis | None = None
        self._config_db: AsyncSession | None = None
        self._tenant_db: AsyncSession | None = None

    @property
    def langfuse_hitl_span(self) -> Any:
        return self._langfuse_hitl_span

    @langfuse_hitl_span.setter
    def langfuse_hitl_span(self, span: Any) -> None:
        self._langfuse_hitl_span = span

    def activate(self) -> None:
        _current.set(self)

    @staticmethod
    def current() -> "RequestContext | None":
        return _current.get()

    async def redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(
                settings.redis_url, decode_responses=True
            )
        return self._redis

    async def config_db(self) -> AsyncSession | None:
        """懒加载配置库会话（mypet_config）."""
        if self._config_db is None:
            self._config_db = ConfigSessionLocal()
        return self._config_db

    async def init_tenant_db(self) -> AsyncSession | None:
        """初始化租户库会话."""
        if self._tenant_db is not None:
            return self._tenant_db
        try:
            session_factory = _get_tenant_engine(self.tenant_code)
            self._tenant_db = session_factory()
        except Exception:
            logger.exception("Failed to init tenant DB")
        return self._tenant_db

    def tenant_db(self) -> AsyncSession | None:
        return self._tenant_db

    async def close(self) -> None:
        """释放所有连接."""
        for db in (self._tenant_db, self._config_db):
            if db:
                try:
                    await db.close()
                except Exception:
                    pass
        self._tenant_db = None
        self._config_db = None
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None
        _current.set(None)
