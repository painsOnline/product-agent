"""
文件名称：checkpointer.py
作者：shop-tool
时间：2026-06-14
逻辑说明：LangGraph Redis Checkpointer，Redis 客户端从外部注入（DIP）.
"""
import logging

from langgraph.checkpoint.redis import RedisSaver
from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from app.conf.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def build_checkpointer(
    redis_client: Redis | AsyncRedis | None = None,
) -> RedisSaver:
    """构建 Redis Checkpointer.

    Args:
        redis_client: Redis 客户端，None 时创建默认客户端
    """
    if redis_client is None:
        redis_client = Redis.from_url(settings.redis_url)

    logger.info("Checkpointer created")
    return RedisSaver(redis_client)
