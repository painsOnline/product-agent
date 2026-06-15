"""
文件名称：auth_service.py
作者：shop-tool
时间：2026-06-14
逻辑说明：鉴权服务，负责 JWT 校验和租户验证.

鉴权流程：
1. 从 Header 读取 Authorization (Bearer token) 和 Tenant
2. 解析 JWT token，验证签名和过期时间
3. 查询 mypet_config 校验租户是否存在、状态是否正常
4. 验证 token 中的 tenantCode 与 Header Tenant 一致
"""
import logging
from typing import Any

from app.conf.constants import StatusCode
from app.conf.database import verify_tenant_and_get_instance as _default_verify_tenant
from app.utils.jwt_utils import decode_token

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """鉴权异常."""

    def __init__(self, code: str, msg: str) -> None:
        self.code = code
        self.msg = msg
        super().__init__(msg)


async def authenticate(
    authorization: str | None,
    tenant_code: str | None,
    *,
    verify_tenant_fn=_default_verify_tenant,
) -> dict[str, Any]:
    """验证用户身份和租户状态.

    Args:
        authorization: Bearer token 字符串
        tenant_code: 租户 code

    Returns:
        包含 user_id, tenant_code, is_admin 的字典

    Raises:
        AuthError: 鉴权失败时抛出
    """
    if not authorization:
        raise AuthError(StatusCode.UNAUTHORIZED, "缺少 Authorization 头")

    if not authorization.startswith("Bearer "):
        raise AuthError(StatusCode.UNAUTHORIZED, "Authorization 格式错误")

    token = authorization[7:]

    payload = decode_token(token)
    if not payload:
        raise AuthError(
            StatusCode.UNAUTHORIZED, "token 无效或已过期，请重新登录"
        )

    token_tenant = payload.get("tenantCode", "")
    user_id = payload.get("sub")
    is_admin = payload.get("isAdmin", False)

    if not user_id:
        raise AuthError(StatusCode.UNAUTHORIZED, "Token 无效：缺少用户标识")
    if not tenant_code:
        raise AuthError(StatusCode.BAD_REQUEST, "缺少 Tenant 头")

    if not is_admin:
        raise AuthError(StatusCode.FORBIDDEN, "仅管理员可操作")

    if token_tenant and token_tenant != tenant_code:
        raise AuthError(
            StatusCode.UNAUTHORIZED,
            "token 租户信息与请求头 Tenant 不一致",
        )

    tenant_info, db_info = await verify_tenant_fn(tenant_code)
    if not tenant_info:
        raise AuthError(StatusCode.BAD_REQUEST, "租户不存在")

    if tenant_info.get("is_disable") == 1:
        raise AuthError(StatusCode.BAD_REQUEST, "租户已被禁用")

    logger.info(
        "Authenticated user_id=%s tenant=%s", user_id, tenant_code
    )

    return {
        "user_id": user_id,
        "tenant_code": tenant_code,
        "is_admin": is_admin,
    }
