"""
文件名称：checkpointer.py
作者：shop-tool
时间：2026-06-15
逻辑说明：LangGraph Redis Checkpointer，使用纯 Redis GET/SET + JSON 序列化，
不依赖 RedisJSON 模块。"""
import json
import logging
from typing import Any

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from redis.asyncio import Redis

from app.conf.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class PlainRedisSaver(BaseCheckpointSaver):
    """基于纯 Redis String 的 Checkpointer，不依赖 RedisJSON."""

    def __init__(self, redis_url: str) -> None:
        super().__init__()
        self._redis: Redis | None = None
        self._redis_url = redis_url

    async def _ensure_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    # config["configurable"]["thread_id"] 格式:
    #   checkpointer:{tenant_code}:{user_id}_{product_id}
    # 从中解出 tenant_code 和原始 thread_id，严格按租户隔离构造 Key.

    @staticmethod
    def _parse_scoped(thread_id: str) -> tuple[str, str]:
        # thread_id = "checkpointer:xlong:admin_631101402521"
        # 去掉 "checkpointer:" 前缀，剩余部分是 "{tenant_code}:{user_thread_id}"
        body = thread_id.removeprefix("checkpointer:")
        parts = body.split(":", 1)
        tenant = parts[0]
        uid = parts[1] if len(parts) > 1 else body
        return tenant, uid

    def _cp_key(self, thread_id: str, checkpoint_id: str) -> str:
        tenant, uid = self._parse_scoped(thread_id)
        return f"checkpointer:{tenant}:{uid}:{checkpoint_id}"

    def _cp_pattern(self, thread_id: str) -> str:
        tenant, uid = self._parse_scoped(thread_id)
        return f"checkpointer:{tenant}:{uid}:*"

    def _writes_key(self, thread_id: str, task_id: str, idx: int) -> str:
        tenant, uid = self._parse_scoped(thread_id)
        return f"checkpointer_writes:{tenant}:{uid}:{task_id}:{idx}"

    def _writes_pattern(self, thread_id: str) -> str:
        tenant, uid = self._parse_scoped(thread_id)
        return f"checkpointer_writes:{tenant}:{uid}:*"

    def _delete_pattern(self, tenant: str) -> str:
        return f"checkpointer:{tenant}:*"

    async def aget_tuple(self, config: dict) -> CheckpointTuple | None:
        redis = await self._ensure_redis()
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id", "")

        if checkpoint_id:
            data = await redis.get(self._cp_key(thread_id, checkpoint_id))
        else:
            keys = await redis.keys(self._cp_pattern(thread_id))
            if not keys:
                return None
            keys.sort()
            data = await redis.get(keys[-1])

        if not data:
            return None

        entry = json.loads(data)
        cp_data = entry["checkpoint"]

        # channel_values 中的 messages 可能被序列化为 dict 列表，
        # Checkpoint 构造器不做 BaseMessage 还原，直接透传。
        checkpoint = Checkpoint(**cp_data) if isinstance(cp_data, dict) else cp_data
        metadata = CheckpointMetadata(**entry.get("metadata", {}))
        return CheckpointTuple(
            config=entry["config"],
            checkpoint=checkpoint,
            metadata=metadata,
        )

    async def aput(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict,
    ) -> dict:
        redis = await self._ensure_redis()
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]

        # 序列化时用 Pydantic model_dump 保留完整 channel_values
        cp_dict = checkpoint if isinstance(checkpoint, dict) else checkpoint
        if hasattr(cp_dict, "model_dump"):
            cp_dict = cp_dict.model_dump()
        meta_dict = metadata if isinstance(metadata, dict) else metadata
        if hasattr(meta_dict, "model_dump"):
            meta_dict = meta_dict.model_dump()

        entry = {
            "config": config,
            "checkpoint": cp_dict,
            "metadata": meta_dict,
            "new_versions": new_versions,
        }

        # debug: 打印 channel_values 中 messages 的实际类型和数量
        channel_vals = cp_dict.get("channel_values", {}) if isinstance(cp_dict, dict) else {}
        msgs = channel_vals.get("messages", [])
        msgs_type = type(msgs).__name__
        msgs_len = len(msgs) if hasattr(msgs, "__len__") else "N/A"
        print(f"[PlainRedisSaver.aput] step={checkpoint_id[-8:]} channel_keys={sorted(channel_vals.keys())} msgs_type={msgs_type} msgs_len={msgs_len}")

        await redis.set(
            self._cp_key(thread_id, checkpoint_id),
            json.dumps(entry, default=str),
        )
        return config

    async def aput_writes(
        self,
        config: dict,
        writes: list[Any],
        task_id: str,
        task_path: str = "",
    ) -> None:
        redis = await self._ensure_redis()
        thread_id = config["configurable"]["thread_id"]
        for idx, write in enumerate(writes):
            await redis.set(
                self._writes_key(thread_id, task_id, idx),
                json.dumps(write, default=str),
            )

    async def alist(
        self,
        config: dict | None,
        *,
        filter: dict | None = None,
        before: dict | None = None,
        limit: int | None = None,
    ) -> list[CheckpointTuple]:
        del filter, before
        if config is None:
            return []

        redis = await self._ensure_redis()
        thread_id = config["configurable"]["thread_id"]
        keys = await redis.keys(self._cp_pattern(thread_id))
        keys.sort()

        if limit and limit > 0:
            keys = keys[-limit:]

        results: list[CheckpointTuple] = []
        for key in keys:
            data = await redis.get(key)
            if data:
                entry = json.loads(data)
                checkpoint = Checkpoint(**entry["checkpoint"])
                metadata = CheckpointMetadata(**entry.get("metadata", {}))
                results.append(CheckpointTuple(
                    config=entry["config"],
                    checkpoint=checkpoint,
                    metadata=metadata,
                ))
        return results

    async def adelete_thread(self, thread_id: str) -> None:
        redis = await self._ensure_redis()
        keys = await redis.keys(self._cp_pattern(thread_id))
        if keys:
            await redis.delete(*keys)
        write_keys = await redis.keys(self._writes_pattern(thread_id))
        if write_keys:
            await redis.delete(*write_keys)


def build_checkpointer(redis_client: object | None = None) -> PlainRedisSaver:
    """构建基于纯 Redis 的 Checkpointer."""
    del redis_client
    logger.info("Checkpointer: PlainRedisSaver")
    return PlainRedisSaver(redis_url=settings.redis_url)
