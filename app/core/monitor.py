"""
文件名称：monitor.py
作者：shop-tool
时间：2026-06-14
逻辑说明：Agent 执行过程监控器，chat_api 中所有 WebSocket 消息推送的统一出口.

前端通过此监控器实时了解 Agent 执行进度，避免长时间无响应导致误认为卡死：
- 步骤通知：告知用户当前执行到哪一步（加载历史 → 分析需求 → 优化标题 → 匹配属性 → 汇总结果）
- 流式推送：推送中间推理文本片段
- 结果推送：结构化最终结果、HITL 确认请求
- 错误通知：各类异常状态

chat_api 中所有 websocket.send_json() 调用均汇聚于此，便于统一管理消息格式和推送逻辑.
"""
import logging
from datetime import datetime, timezone

from app.conf.constants import WSMessageType

logger = logging.getLogger(__name__)


class AgentMonitor:
    """Agent 执行监控器，封装所有 WebSocket 消息推送."""

    def __init__(self, websocket) -> None:
        """初始化监控器.

        Args:
            websocket: FastAPI WebSocket 实例
        """
        self._ws = websocket

    async def _send(self, payload: dict) -> None:
        """内部发送方法，静默处理推送失败."""
        try:
            await self._ws.send_json(payload)
        except Exception:
            pass

    # ==================== 心跳 ====================

    async def send_heartbeat(self) -> None:
        """发送心跳包，前端 35s 未收到则判定断连."""
        await self._send({
            "type": WSMessageType.HEARTBEAT,
            "time": datetime.now(timezone.utc).isoformat(),
        })

    # ==================== 错误 ====================

    async def send_error(self, code: str, msg: str) -> None:
        """发送错误消息.

        Args:
            code: 状态码，见 StatusCode 枚举
            msg: 错误描述
        """
        await self._send({
            "type": WSMessageType.ERROR,
            "code": code,
            "msg": msg,
        })

    # ==================== 执行步骤 ====================

    async def send_step(
        self, step: str, status: str, detail: str = ""
    ) -> None:
        """推送执行步骤通知，告知用户当前进度.

        Args:
            step: 步骤名 (history_loading / agent_analyzing /
                  title_optimizing / attribute_matching / summarizing)
            status: 状态 (running / done / failed)
            detail: 补充描述文本
        """
        await self._send({
            "type": WSMessageType.STEP,
            "step": step,
            "status": status,
            "detail": detail,
        })

    async def send_stream(self, content: str) -> None:
        """推送中间推理文本片段.

        Args:
            content: 推理文本，最大 500 字符
        """
        await self._send({
            "type": WSMessageType.STREAM,
            "content": str(content)[:500],
        })

    # ==================== 结果 ====================

    async def send_final(self, data: dict) -> None:
        """推送 Agent 最终结构化输出.

        Args:
            data: 经过 Pydantic 校验的 SupervisorOutput 字典
        """
        await self._send({
            "type": WSMessageType.FINAL,
            "data": data,
        })

    async def send_confirm(
        self,
        thread_id: str,
        import_product_id: str,
        user_id: str,
        timeout: int,
        data: dict,
    ) -> None:
        """推送 HITL 确认请求，等待用户确认/取消.

        Args:
            thread_id: 会话 ID
            import_product_id: 导入商品 ID
            user_id: 用户 ID
            timeout: 超时秒数
            data: 待确认的结构化结果
        """
        await self._send({
            "type": WSMessageType.CONFIRM,
            "thread_id": thread_id,
            "import_product_id": import_product_id,
            "user_id": user_id,
            "timeout": timeout,
            "content": "是否应用本次修改？超时10分钟自动取消",
            "data": data,
        })

    async def send_result(self, content: str) -> None:
        """推送确认/取消后的结果消息.

        Args:
            content: 结果描述文本
        """
        await self._send({
            "type": WSMessageType.STREAM,
            "content": content,
        })
