"""
文件名称：action_log_writer.py
作者：shop-tool
时间：2026-06-14
逻辑说明：Agent 行为日志异步写入器，user_id/import_product_id/db 从 ctx 获取.
"""
import logging

from app.core.context import RequestContext
from app.utils.id_utils import str_to_uuid

logger = logging.getLogger(__name__)


async def write_action_log(
    ctx: RequestContext,
    action_type: str,
    status: str,
    request_data: dict,
    response_data: dict,
    metadata: dict | None = None,
) -> None:
    try:
        from app.models.agent_action_log import AgentActionLog

        db = ctx.tenant_db()
        if db is None:
            return
        log_entry = AgentActionLog(
            user_id=str_to_uuid(ctx.user_id),
            import_product_id=str_to_uuid(ctx.import_product_id),
            action_type=action_type,
            status=status,
            request=request_data,
            response=response_data,
            extra=metadata or {},
        )
        db.add(log_entry)
        await db.commit()
    except Exception as e:
        logger.error("Failed to write action log: %s", e)
