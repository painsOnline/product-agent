"""
文件名称：action_log_repo.py
作者：shop-tool
时间：2026-06-14
逻辑说明：Agent 行为日志仓储，封装 t_agent_action_logs 表的写入操作.
"""
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_action_log import AgentActionLog

logger = logging.getLogger(__name__)


async def create_log(
    db: AsyncSession,
    user_id: uuid.UUID,
    import_product_id: uuid.UUID,
    action_type: str,
    status: str,
    request: dict,
    response: dict,
    metadata: dict | None = None,
) -> AgentActionLog:
    """创建 Agent 行为日志."""
    log_entry = AgentActionLog(
        user_id=user_id,
        import_product_id=import_product_id,
        action_type=action_type,
        status=status,
        request=request,
        response=response,
        extra=metadata or {},
    )
    db.add(log_entry)
    await db.flush()
    await db.refresh(log_entry)
    return log_entry
