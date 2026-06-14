"""
文件名称：protocols.py
作者：shop-tool
时间：2026-06-14
逻辑说明：仓储层抽象协议，定义 Service 依赖的接口.

使用 typing.Protocol 实现结构子类型（structural subtyping），
现有 repo 模块的导出函数天然满足这些协议，无需修改 repo 层代码。

Service 层通过可选参数注入协议实例，默认值绑定具体 repo 模块，
保持向后兼容的同时实现依赖倒置（DIP）.
"""
import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_action_log import AgentActionLog
from app.models.chat_message import ChatMessage
from app.models.ext_product import ExtProductImportLog
from app.models.shop_llm_config import ShopLLMConfig


class ProductRepository(Protocol):
    """商品数据仓储接口."""

    async def get_by_ext_product_id(
        self, db: AsyncSession, ext_from: str, ext_product_id: str
    ) -> ExtProductImportLog | None: ...

    async def get_by_id(
        self, db: AsyncSession, product_id: uuid.UUID
    ) -> ExtProductImportLog | None: ...

    async def create_product(
        self,
        db: AsyncSession,
        ext_from: str,
        ext_product_id: str,
        ext_product_name: str,
        main_picture: str,
        pictures: list[str],
        detail_pictures: list[str],
        attrs: dict,
    ) -> ExtProductImportLog: ...

    async def update_product(
        self, db: AsyncSession, product: ExtProductImportLog, **kwargs
    ) -> ExtProductImportLog: ...

    async def list_products(
        self,
        db: AsyncSession,
        ext_from: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[ExtProductImportLog], int]: ...


class ChatRepository(Protocol):
    """会话记录仓储接口."""

    async def create_message(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        import_product_id: uuid.UUID,
        role: str,
        content: dict,
    ) -> ChatMessage: ...

    async def get_history(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        import_product_id: uuid.UUID,
        limit: int = 50,
    ) -> list[ChatMessage]: ...

    async def get_messages_by_thread(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        import_product_id: uuid.UUID,
    ) -> list[ChatMessage]: ...


class ActionLogRepository(Protocol):
    """Agent 行为日志仓储接口."""

    async def create_log(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        import_product_id: uuid.UUID,
        action_type: str,
        status: str,
        request: dict,
        response: dict,
        metadata: dict | None = None,
    ) -> AgentActionLog: ...


class LLMConfigRepository(Protocol):
    """LLM 配置仓储接口."""

    async def get_active_config(
        self, db: AsyncSession
    ) -> ShopLLMConfig | None: ...
