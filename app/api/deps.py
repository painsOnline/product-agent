"""
文件名称：deps.py
作者：shop-tool
时间：2026-06-14
逻辑说明：FastAPI 依赖注入，处理 JWT 鉴权和租户数据库会话.
"""
import logging
from typing import AsyncGenerator, Any

from fastapi import Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.conf.database import get_tenant_session
from app.services.auth_service import AuthError, authenticate

logger = logging.getLogger(__name__)


async def get_current_user(
    authorization: str | None = Header(None),
    tenant: str | None = Header(None),
) -> dict[str, Any]:
    """从请求头提取并验证用户身份.

    Raises:
        AuthError: 鉴权失败
    """
    return await authenticate(authorization, tenant)


async def get_db(
    tenant: str = Header(...),
) -> AsyncGenerator[AsyncSession, None]:
    """获取当前租户的数据库会话."""
    if not tenant:
        raise AuthError("400", "缺少 Tenant 头")

    async for session in get_tenant_session(tenant):
        yield session
