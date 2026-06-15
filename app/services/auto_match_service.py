"""
文件名称：auto_match_service.py
作者：shop-tool
时间：2026-06-14
逻辑说明：商品自动匹配服务，构建 AgentState 传入 Supervisor Graph.
"""
import json as _json
import logging

from app.agent.main_agent import get_agent
from app.core.state_factory import StateFactory
from app.conf.constants import CHECKPOINT_PREFIX, OperateType
from app.core.context import RequestContext
from app.repositories.llm_config_repo import get_active_config_dict
from app.services import product_service
from app.services.chat_history_service import (
    save_assistant_message,
    save_user_message,
)

logger = logging.getLogger(__name__)
_state_factory = StateFactory()


async def auto_match(
    ctx: RequestContext,
    ext_from: str,
    ext_product_id: str,
    target_attrs: list[dict] | None = None,
) -> dict:
    """Agent 自动匹配商品标题和属性."""
    db = ctx.tenant_db()
    if db is None:
        raise RuntimeError("租户库未初始化")

    product = await product_service.get_product(db, ext_from, ext_product_id)
    if not product:
        raise ValueError(f"商品未找到: {ext_from}/{ext_product_id}")

    origin_title = product.ext_product_name
    original_attrs = product.attrs or {}

    user_content = "请优化商品标题并匹配属性"
    await save_user_message(
        ctx,
        user_content=user_content,
        operate_type=OperateType.BOTH,
        original_title=origin_title,
        original_attrs=original_attrs,
        target_attrs=target_attrs or [],
    )

    # AgentState
    input_state = _state_factory.auto_match(
        thread_id=ctx.thread_id,
        user_id=ctx.user_id,
        import_product_id=ctx.import_product_id,
        original_title=origin_title,
        original_attrs=original_attrs,
        target_attrs=target_attrs or [],
    )

    llm_config = await get_active_config_dict(db)
    if not llm_config:
        raise RuntimeError("未找到 LLM 配置")

    scoped_thread_id = f"{CHECKPOINT_PREFIX}{ctx.tenant_code}:auto_{ctx.thread_id}"
    agent = get_agent(
        scoped_thread_id,
        llm_config=llm_config,
        redis_client=await ctx.redis(),
    )
    await agent.checkpointer.adelete_thread(scoped_thread_id)
    config = {"configurable": {"thread_id": scoped_thread_id}, "recursion_limit": 15}

    result = await agent.ainvoke(input_state, config=config)

    validated = _extract(result, origin_title)
    await save_assistant_message(ctx, validated)

    return {
        "new_title": validated.get("new_title", ""),
        "original_title": origin_title,
        "title_note": validated.get("title_note", ""),
        "attr_mapping": validated.get("attr_mapping", []),
        "warning": validated.get("warning", {"has_warn": False, "warn_content": ""}),
        "suggestion": validated.get("suggestion", {"summary": "", "items": []}),
    }


def _extract(result: dict, origin_title: str) -> dict:
    lr = result.get("latest_result") if isinstance(result, dict) else None
    if lr and isinstance(lr, dict) and lr.get("new_title"):
        return lr

    msgs = result.get("messages", []) if isinstance(result, dict) else []
    for msg in reversed(msgs):
        content = getattr(msg, "content", "")
        if not isinstance(content, str) or "new_title" not in content:
            continue
        try:
            cleaned = content.strip()
            if cleaned.startswith("```"):
                idx = cleaned.find("\n")
                cleaned = cleaned[idx + 1:] if idx > 0 else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed = _json.loads(cleaned.strip())
            if isinstance(parsed, dict) and "new_title" in parsed:
                return parsed
        except Exception:
            pass

    return {
        "new_title": origin_title,
        "original_title": origin_title,
        "title_note": "Agent 未返回有效结果",
        "attr_mapping": [],
        "warning": {"has_warn": True, "warn_content": "Agent 未返回有效结果"},
        "suggestion": {"summary": "", "items": []},
    }
