"""
文件名称：state_factory.py
作者：shop-tool
时间：2026-06-15
逻辑说明：AgentState 初始值工厂，封装聊天和自动匹配两种场景的状态构建.
"""
from typing import Any

from langchain_core.messages import HumanMessage

from app.conf.constants import OperateType as _O


class StateFactory:
    """AgentState 初始状态工厂.

    用法:
        factory = StateFactory()
        state = factory.chat(thread_id=..., ...)
        state = factory.auto_match(thread_id=..., ...)
    """

    @staticmethod
    def _base(
        thread_id: str = "",
        user_id: str = "",
        import_product_id: str = "",
        operate_type: str = _O.BOTH,
        original_title: str = "",
        original_attrs: list[dict[str, Any]] | None = None,
        target_attrs: list[dict[str, Any]] | None = None,
        user_content: str = "",
        manual_data: dict[str, Any] | None = None,
        title_max_len: int = 45,
        ban_words: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "thread_id": thread_id,
            "user_id": user_id,
            "import_product_id": import_product_id,
            "operate_type": operate_type,
            "original_title": original_title,
            "original_attrs": original_attrs or [],
            "target_attrs": target_attrs or [],
            "title_max_len": title_max_len,
            "ban_words": ban_words or [],
            "user_content": user_content,
            "manual_data": manual_data,
            "latest_result": {},
            "current_step": "idle",
            "hitl_status": "none",
            "error_info": None,
            "messages": [],
            "remaining_steps": 10,
        }

    def chat(
        self,
        thread_id: str,
        user_id: str,
        import_product_id: str,
        operate_type: str,
        original_title: str,
        original_attrs: list[dict[str, Any]],
        target_attrs: list[dict[str, Any]],
        user_content: str,
        manual_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """WebSocket 聊天会话初始状态."""
        state = self._base(
            thread_id=thread_id, user_id=user_id,
            import_product_id=import_product_id, operate_type=operate_type,
            original_title=original_title, original_attrs=original_attrs,
            target_attrs=target_attrs, user_content=user_content,
            manual_data=manual_data,
        )
        state["messages"] = [HumanMessage(content=user_content or "请优化商品标题并匹配属性")]
        return state

    def auto_match(
        self,
        thread_id: str,
        user_id: str,
        import_product_id: str,
        original_title: str,
        original_attrs: list[dict[str, Any]],
        target_attrs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """自动匹配（非 WebSocket）初始状态."""
        user_content = "请优化商品标题并匹配属性"
        state = self._base(
            thread_id=thread_id, user_id=user_id,
            import_product_id=import_product_id, operate_type=_O.BOTH,
            original_title=original_title, original_attrs=original_attrs,
            target_attrs=target_attrs or [], user_content=user_content,
        )
        state["messages"] = [HumanMessage(content=user_content)]
        return state
