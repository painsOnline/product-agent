"""
文件名称：chat_history_service.py
作者：shop-tool
时间：2026-06-14
逻辑说明：会话历史服务，db/user_id/import_product_id 统一从 RequestContext 获取.
"""
import json
import logging
import uuid

from app.conf.constants import ChatRole, OperateType
from app.core.context import RequestContext
from app.repositories import chat_repo
from app.repositories.protocols import ChatRepository

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_LIMIT = 10


def _fmt(content: dict | str) -> str:
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return str(content)


def build_agent_input(
    user_content: str,
    operate_type: str,
    origin_title: str,
    origin_attrs: list[dict],
) -> str:
    """构造 Agent 输入文本（纯函数，无外部依赖）."""
    return (
        f"[operate_type={operate_type}]\n"
        f"用户要求：{user_content}\n"
        f"原始商品标题：{origin_title}\n"
        f"原始商品属性：{json.dumps(origin_attrs, ensure_ascii=False)}"
    )


async def load_chat_history(
    ctx: RequestContext,
    limit: int = DEFAULT_HISTORY_LIMIT,
    *,
    repo: ChatRepository = chat_repo,
) -> list[dict]:
    db = ctx.tenant_db()
    if db is None:
        return []
    try:
        history = await repo.get_messages_by_thread(
            db, uuid.UUID(ctx.user_id), uuid.UUID(ctx.import_product_id)
        )
    except Exception:
        logger.exception("Failed to load chat history")
        return []

    messages: list[dict] = []
    for h in history[-limit:]:
        role = "assistant" if h.role == ChatRole.ASSISTANT else "user"
        messages.append({"role": role, "content": _fmt(h.content)})
    logger.info("Loaded %d history for %s/%s", len(messages), ctx.user_id, ctx.import_product_id)
    return messages


async def save_user_message(
    ctx: RequestContext,
    *,
    user_content: str,
    operate_type: str = OperateType.BOTH,
    origin_title: str = "",
    origin_attrs: list[dict] | None = None,
    repo: ChatRepository = chat_repo,
) -> None:
    db = ctx.tenant_db()
    if db is None:
        return
    try:
        await repo.create_message(
            db,
            user_id=uuid.UUID(ctx.user_id),
            import_product_id=uuid.UUID(ctx.import_product_id),
            role=ChatRole.USER,
            content={
                "type": "chat",
                "user_content": user_content,
                "operate_type": operate_type,
                "origin_title": origin_title,
                "origin_attrs": origin_attrs or [],
            },
        )
        await db.commit()
    except Exception:
        logger.exception("Failed to save user message")


async def save_assistant_message(
    ctx: RequestContext,
    validated_dict: dict,
    *,
    repo: ChatRepository = chat_repo,
) -> None:
    db = ctx.tenant_db()
    if db is None:
        return
    try:
        await repo.create_message(
            db,
            user_id=uuid.UUID(ctx.user_id),
            import_product_id=uuid.UUID(ctx.import_product_id),
            role=ChatRole.ASSISTANT,
            content={"type": "final", "data": validated_dict},
        )
        await db.commit()
    except Exception:
        logger.exception("Failed to save assistant message")


async def save_confirm_reply(
    ctx: RequestContext,
    operate_result: str,
    *,
    repo: ChatRepository = chat_repo,
) -> None:
    db = ctx.tenant_db()
    if db is None:
        return
    try:
        await repo.create_message(
            db,
            user_id=uuid.UUID(ctx.user_id),
            import_product_id=uuid.UUID(ctx.import_product_id),
            role=ChatRole.USER,
            content={"type": "confirm_reply", "result": operate_result},
        )
        await db.commit()
    except Exception:
        logger.exception("Failed to save confirm reply")
