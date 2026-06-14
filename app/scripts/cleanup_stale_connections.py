"""
文件名称：cleanup_stale_connections.py
作者：shop-tool
时间：2026-06-14
逻辑说明：定时任务脚本，清理残留的 ws:online/* 和死锁.

通过 Redis Key 过期监听 + 定时巡检，清理假死连接和过期锁.
"""
import asyncio
import logging

from redis.asyncio import Redis

from app.conf.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

WS_ONLINE_PREFIX = "ws:online:"
BIZ_LOCK_PREFIX = "biz:lock:session:"


async def cleanup_stale_keys() -> None:
    """定时巡检，清理过期残留 key."""
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        pattern = f"{WS_ONLINE_PREFIX}*"
        keys = []
        async for key in redis.scan_iter(match=pattern):
            keys.append(key)

        for key in keys:
            ttl = await redis.ttl(key)
            if ttl < 0:
                logger.warning("Cleaning stale WS key: %s", key)
                await redis.delete(key)

        lock_pattern = f"{BIZ_LOCK_PREFIX}*"
        async for key in redis.scan_iter(match=lock_pattern):
            ttl = await redis.ttl(key)
            if ttl < 0:
                logger.warning("Cleaning stale lock key: %s", key)
                await redis.delete(key)

    finally:
        await redis.aclose()


async def main() -> None:
    """定时任务入口."""
    logger.info("Starting cleanup task")
    await cleanup_stale_keys()
    logger.info("Cleanup task completed")


if __name__ == "__main__":
    asyncio.run(main())
