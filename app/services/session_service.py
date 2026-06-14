"""
文件名称：session_service.py
作者：shop-tool
时间：2026-06-14
逻辑说明：会话管理服务，redis/tenant_code/thread_id 统一从 RequestContext 获取.
"""
import asyncio
import logging
import uuid

from app.conf.constants import WS_CONNECTION_TTL
from app.conf.settings import get_settings
from app.core.context import RequestContext

logger = logging.getLogger(__name__)

settings = get_settings()

_WS_KEY = "ws:online:{}:{}"
_LOCK_KEY = "biz:lock:session:{}:{}"


def _ws_key(ctx: RequestContext) -> str:
    return _WS_KEY.format(ctx.tenant_code, ctx.thread_id)


def _lock_key(ctx: RequestContext) -> str:
    return _LOCK_KEY.format(ctx.tenant_code, ctx.thread_id)


async def register_connection(ctx: RequestContext, conn_id: str) -> bool:
    redis = await ctx.redis()
    key = _ws_key(ctx)
    existing = await redis.get(key)
    if existing:
        logger.warning("Connection exists: key=%s existing=%s", key, existing)
        return False
    await redis.setex(key, WS_CONNECTION_TTL, conn_id)
    logger.info("WS connected: key=%s", key)
    return True


async def unregister_connection(ctx: RequestContext) -> None:
    redis = await ctx.redis()
    await redis.delete(_ws_key(ctx))
    logger.info("WS disconnected: key=%s", _ws_key(ctx))


async def refresh_connection(ctx: RequestContext, conn_id: str) -> None:
    redis = await ctx.redis()
    key = _ws_key(ctx)
    current = await redis.get(key)
    if current == conn_id:
        await redis.setex(key, WS_CONNECTION_TTL, conn_id)


async def acquire_lock(ctx: RequestContext) -> bool:
    redis = await ctx.redis()
    key = _lock_key(ctx)
    lock_value = str(uuid.uuid4())
    acquired = await redis.set(key, lock_value, nx=True, ex=settings.agent_lock_timeout)
    if acquired:
        logger.info("Lock acquired: key=%s", key)
    else:
        logger.warning("Lock conflict: key=%s", key)
    return bool(acquired)


async def release_lock(ctx: RequestContext) -> None:
    redis = await ctx.redis()
    await redis.delete(_lock_key(ctx))
    logger.info("Lock released: key=%s", _lock_key(ctx))


async def wait_for_lock(ctx: RequestContext) -> bool:
    deadline = asyncio.get_event_loop().time() + settings.agent_lock_wait_timeout
    while asyncio.get_event_loop().time() < deadline:
        if await acquire_lock(ctx):
            return True
        await asyncio.sleep(1)
    logger.error("Lock wait timeout: key=%s", _lock_key(ctx))
    return False
