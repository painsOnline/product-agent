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
