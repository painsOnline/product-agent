"""
文件名称：jwt_utils.py
作者：shop-tool
时间：2026-06-14
逻辑说明：JWT 编解码工具，使用 PyJWT 实现.

Token 格式：
- sub: userId
- claims: tenantCode, isAdmin
- expiration 通过 jwt.expiration 配置
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.conf.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def create_token(
    user_id: str,
    tenant_code: str,
    is_admin: bool = True,
) -> str:
    """创建 JWT token.

    Args:
        user_id: 用户ID，作为 subject
        tenant_code: 租户 code
        is_admin: 是否管理员

    Returns:
        JWT token 字符串
    """
    payload = {
        "sub": user_id,
        "tenantCode": tenant_code,
        "isAdmin": is_admin,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc)
        + timedelta(seconds=settings.jwt_expiration),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm="HS256",
    )
    return token


def decode_token(token: str) -> dict[str, Any] | None:
    """解码 JWT token，验证签名和过期时间.

    Returns:
        解码后的 payload 字典，验证失败返回 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token: %s", e)
        return None
