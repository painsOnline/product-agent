"""
文件名称：constants.py
作者：shop-tool
时间：2026-06-14
逻辑说明：全局常量与枚举值定义.
"""


class StatusCode:
    """API 返回状态码."""
    SUCCESS = "200"
    BAD_REQUEST = "400"
    UNAUTHORIZED = "401"
    FORBIDDEN = "403"
    NOT_FOUND = "404"
    METHOD_NOT_ALLOWED = "405"
    SESSION_BUSY = "406"
    HITL_TIMEOUT = "407"
    REQUEST_TIMEOUT = "408"
    SESSION_CONFLICT = "409"
    LOCKED = "423"
    RATE_LIMIT = "429"
    SERVER_ERROR = "500"
    GATEWAY_ERROR = "502"
    LLM_BUSY = "503"
    PARSE_ERROR = "506"
    SUB_AGENT_ERROR = "507"


class Platform:
    """第三方平台类型."""
    ALIBABA_1688 = "1688"
    TAOBAO = "taobao"


class ActionType:
    """Agent 行为日志类型."""
    LLM_INVOKE = "llm_invoke"
    CONTEXT_COMPRESS = "context_compress"
    PARSE_ERROR = "parse_error"
    LLM_TIMEOUT = "llm_timeout"
    HITL_CONFIRM = "hitl_confirm"
    HITL_TIMEOUT = "hitl_timeout"


class ActionStatus:
    """动作状态."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"


class ChatRole:
    """会话角色."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class OperateType:
    """操作类型."""
    REWRITE_TITLE = "rewrite_title"
    MATCH_ATTR = "match_attr"
    BOTH = "both"


class WSMessageType:
    """WebSocket 消息类型."""
    CHAT = "chat"
    CONFIRM_REPLY = "confirm_reply"
    STREAM = "stream"
    STEP = "step"
    FINAL = "final"
    RESPOND = "respond"
    CONFIRM = "confirm"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class SessionStep:
    """会话执行步骤."""
    IDLE = "idle"
    RUNNING = "running"
    CONFIRM = "confirm"
    FINISHED = "finished"
    FAILED = "failed"


class HitlStatus:
    """HITL 确认状态."""
    NONE = "none"
    PENDING = "pending"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    TIMEOUT = "timeout"


# 图片下载配置
IMAGE_DOWNLOAD_TIMEOUT = 10
IMAGE_DOWNLOAD_RETRIES = 1
IMAGE_DOWNLOAD_DELAY_MIN = 1.0   # 下载间隔最小秒数
IMAGE_DOWNLOAD_DELAY_MAX = 3.0   # 下载间隔最大秒数

# Checkpointer Key 前缀
CHECKPOINT_PREFIX = "checkpointer:"

# WebSocket 心跳配置
WS_HEARTBEAT_INTERVAL = 20
WS_CLIENT_HEARTBEAT_TIMEOUT = 35
WS_CONNECTION_TTL = 30

# 上下文压缩阈值 (50%)
CONTEXT_COMPRESS_THRESHOLD = 0.5
