"""
文件名称：database.py
作者：shop-tool
时间：2026-06-14
逻辑说明：数据库引擎管理，动态租户库路由.

租户库校验连接逻辑：
- 从 Header 读取 Tenant + Authorization
- 先查询配置库 mypet_config 校验租户是否存在、状态是否正常
- 不存在 / 禁用直接返回 400 租户不存在
- 动态创建 SQLAlchemy Session 绑定到 mypet_{租户code} 租户库
"""
import logging
from typing import AsyncGenerator

from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.conf.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_config_engine = create_async_engine(
    settings.db_url_config,
    echo=False,
    poolclass=NullPool,
)

ConfigSessionLocal = async_sessionmaker(
    _config_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

_tenant_engines: dict[str, object] = {}
_tenant_sessions: dict[str, async_sessionmaker] = {}


def _get_tenant_db_url(tenant_code: str) -> str:
    """根据租户code生成数据库连接URL."""
    return settings.db_url_template.format(tenant_code=tenant_code)


def _get_tenant_engine(tenant_code: str):
    """获取或创建租户数据库引擎."""
    if tenant_code not in _tenant_engines:
        db_url = _get_tenant_db_url(tenant_code)
        _tenant_engines[tenant_code] = create_async_engine(
            db_url,
            echo=False,
            poolclass=NullPool,
        )
        _tenant_sessions[tenant_code] = async_sessionmaker(
            _tenant_engines[tenant_code],
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _tenant_sessions[tenant_code]


async def get_config_session() -> AsyncGenerator[AsyncSession, None]:
    """获取配置库会话."""
    async with ConfigSessionLocal() as session:
        yield session


async def get_tenant_session(tenant_code: str) -> AsyncGenerator[AsyncSession, None]:
    """获取租户库会话.

    使用前需先校验租户状态.
    """
    if not tenant_code:
        raise ValueError("tenant_code 不能为空")
    session_factory = _get_tenant_engine(tenant_code)
    async with session_factory() as session:
        yield session


async def verify_tenant(tenant_code: str) -> dict | None:
    """校验租户是否存在且状态正常.

    从 mypet_config.c_tenant 查询租户信息.
    返回租户信息字典或 None.
    """
    async with ConfigSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT id, code, name, is_disable, is_bussiness_open "
                "FROM c_tenant WHERE code = :code"
            ),
            {"code": tenant_code},
        )
        row = result.fetchone()
        if not row:
            return None
        tenant_info = {
            "id": str(row[0]),
            "code": row[1],
            "name": row[2],
            "is_disable": row[3],
            "is_bussiness_open": row[4],
        }
        if tenant_info["is_disable"] == 1:
            logger.warning("Tenant %s is disabled", tenant_code)
            return None
        return tenant_info


async def verify_tenant_and_get_instance(tenant_code: str) -> tuple[dict | None, dict | None]:
    """校验租户并返回数据库实例信息.

    Returns:
        (tenant_info, db_instance_info)
    """
    async with ConfigSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT t.id, t.code, t.name, t.is_disable, t.is_bussiness_open, "
                "t.database_instance_id "
                "FROM c_tenant t WHERE t.code = :code"
            ),
            {"code": tenant_code},
        )
        row = result.fetchone()
        if not row:
            return None, None
        tenant_info = {
            "id": str(row[0]),
            "code": row[1],
            "name": row[2],
            "is_disable": row[3],
            "is_bussiness_open": row[4],
        }
        if tenant_info["is_disable"] == 1:
            return tenant_info, None
        db_instance_id = str(row[5])
        db_result = await session.execute(
            text(
                "SELECT id, host, port, \"user\", password "
                "FROM c_database_instance WHERE id = :id"
            ),
            {"id": db_instance_id},
        )
        db_row = db_result.fetchone()
        if not db_row:
            return tenant_info, None
        db_info = {
            "id": str(db_row[0]),
            "host": db_row[1],
            "port": db_row[2],
            "user": db_row[3],
            "password": db_row[4],
        }
        return tenant_info, db_info


async def dispose_engines() -> None:
    """释放所有数据库引擎."""
    await _config_engine.dispose()
    for engine in _tenant_engines.values():
        await engine.dispose()
    _tenant_engines.clear()
    _tenant_sessions.clear()
