"""
文件名称：context.py
作者：shop-tool
时间：2026-06-14
逻辑说明：请求级上下文对象，每个请求一个实例，统一管理 Redis + PG 连接和用户身份.

设计要点：
- 一个 WebSocket 连接 / HTTP 请求 → 一个 RequestContext 实例
- 实例挂载到 contextvars，协程安全
- Redis、config 库、租户库全部懒加载，全链路复用
"""
import contextvars
import logging

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.conf.database import get_config_session, get_tenant_session
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
        tenant_code: str = "",
        user_id: str = "",
        import_product_id: str = "",
    ) -> None:
        self.tenant_code = tenant_code
        self.user_id = user_id
        self.import_product_id = import_product_id
        self.thread_id: str = ""

        self._redis: Redis | None = None
        self._config_db: AsyncSession | None = None
        self._tenant_db: AsyncSession | None = None

    # ---- 激活 ----

    def activate(self) -> None:
        """注册为当前协程的全局上下文."""
        _current.set(self)

    @staticmethod
    def current() -> "RequestContext | None":
        """获取当前协程的 RequestContext."""
        return _current.get()

    # ---- Redis ----

    async def redis(self) -> Redis:
        """懒加载 Redis 客户端."""
        if self._redis is None:
            self._redis = Redis.from_url(
                settings.redis_url, decode_responses=True
            )
        return self._redis

    # ---- 配置库 ----

    async def config_db(self) -> AsyncSession | None:
        """懒加载配置库会话（mypet_config）."""
        if self._config_db is None:
            try:
                async for session in get_config_session():
                    self._config_db = session
                    break
            except Exception:
                logger.exception("Failed to init config DB")
        return self._config_db

    # ---- 租户库 ----

    async def init_tenant_db(self) -> AsyncSession | None:
        """初始化租户库会话."""
        if self._tenant_db is not None:
            return self._tenant_db
        try:
            async for session in get_tenant_session(self.tenant_code):
                self._tenant_db = session
                return session
        except Exception:
            logger.exception("Failed to init tenant DB")
            return None

    def tenant_db(self) -> AsyncSession | None:
        """获取租户库会话（需先调用 init_tenant_db）."""
        return self._tenant_db

    # ---- 释放 ----

    async def close(self) -> None:
        """释放所有连接."""
        for db in (self._tenant_db, self._config_db):
            if db:
                try:
                    await db.close()
                except Exception:
                    pass
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                pass
        _current.set(None)
        _current.set(None)
