"""
文件名称：llm_config_repo.py
作者：shop-tool
时间：2026-06-14
逻辑说明：LLM 配置仓储，从 t_shop_llm_config 表读取配置.
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shop_llm_config import ShopLLMConfig

logger = logging.getLogger(__name__)


async def get_active_config(db: AsyncSession) -> ShopLLMConfig | None:
    """获取当前有效的 LLM 配置（取最新一条）."""
    stmt = (
        select(ShopLLMConfig)
        .order_by(ShopLLMConfig.create_time.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def config_to_dict(config: ShopLLMConfig) -> dict:
    """将 ORM 对象转为 create_llm() 所需的字典格式."""
    return {
        "provider": config.provider,
        "api_key": config.api_key,
        "model_name": config.model_name,
        "base_url": config.base_url,
        "temperature": float(config.temperature),
        "max_tokens": config.max_tokens,
        "timeout_seconds": config.timeout_seconds,
        "max_retries": config.max_retries,
    }


async def get_active_config_dict(db: AsyncSession) -> dict | None:
    """获取当前有效的 LLM 配置字典."""
    config = await get_active_config(db)
    return config_to_dict(config) if config else None
