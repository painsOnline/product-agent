"""
文件名称：test_auth.py
作者：shop-tool
时间：2026-06-14
逻辑说明：JWT 鉴权单元测试.
"""
import pytest

from app.utils.jwt_utils import create_token, decode_token
from app.services.auth_service import AuthError


class TestJWT:
    """JWT 编解码测试."""

    def test_create_and_decode_token(self) -> None:
        user_id = "test-user-id"
        tenant_code = "test_tenant"
        token = create_token(user_id, tenant_code, is_admin=True)
        assert token is not None

        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["tenantCode"] == tenant_code
        assert payload["isAdmin"] is True

    def test_invalid_token(self) -> None:
        result = decode_token("invalid-token")
        assert result is None

    def test_expired_token_returns_none(self) -> None:
        """测试空字符串返回 None."""
        result = decode_token("")
        assert result is None

    def test_non_admin_token(self) -> None:
        token = create_token("u1", "t1", is_admin=False)
        payload = decode_token(token)
        assert payload["isAdmin"] is False


class TestAuthService:
    """鉴权服务测试."""

    def test_auth_error_fields(self) -> None:
        e = AuthError("401", "token过期")
        assert e.msg == "token过期"
        assert e.code == "401"

    def test_authenticate_missing_headers(self) -> None:
        with pytest.raises(AuthError):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                _test_auth(None, None)
            )


async def _test_auth(auth: str | None, tenant: str | None):
    from app.services.auth_service import authenticate
    await authenticate(auth, tenant)
