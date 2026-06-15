"""
文件名称：chat.py
作者：shop-tool
时间：2026-06-15
逻辑说明：WebSocket 聊天消息实体定义.
"""
from pydantic import BaseModel, Field


class TargetAttr(BaseModel):
    """目标平台属性项（前端从街顺 DOM 采集）."""
    channel: str = Field("", description="渠道：美团/淘宝闪购")
    target_name: str = Field("", description="属性名称")
    target_interaction_type: str = Field(
        "", description="交互类型：无限制输入框/限制性输入框/单选/多选"
    )
    target_optional_values: list[str] = Field(
        default_factory=list, description="可选值列表"
    )
    target_value_type: str = Field(
        "", description="值类型：字符串/整数/小数/日期/金额"
    )


class OriginAttr(BaseModel):
    """源平台属性项（1688/淘宝原始属性），值现在是数组."""
    source_name: str = Field(..., description="原始属性名称")
    source_value: list[str] = Field(default_factory=list, description="原始属性值")


class AttrItem(BaseModel):
    """属性项（兼容旧代码）."""
    source_name: str = Field(..., description="原始属性名称")
    source_value: str = Field(..., description="原始属性值")


class AttrMapping(BaseModel):
    """属性映射结果 — 值改为数组，新增 channel."""
    channel: str = Field("", description="渠道：美团/淘宝闪购")
    target_name: str = Field("", description="匹配后的属性名")
    target_value: list[str] = Field(default_factory=list, description="匹配后的属性值")
    source_name: str = Field("", description="原始的属性名")
    source_value: list[str] = Field(default_factory=list, description="原始的属性值")
    map_note: str = Field("", description="匹配说明")


class ManualData(BaseModel):
    """用户手动修改后的数据."""
    new_title: str = Field("", description="更新后的标题")
    attr_mapping: list[AttrMapping] = Field(
        default_factory=list, description="匹配后的属性"
    )


class ChatRequest(BaseModel):
    """客户端 → 服务端 chat 消息."""
    type: str = Field("chat", description="消息类型")
    thread_id: str = Field(..., description="会话唯一标识")
    import_product_id: str = Field(..., description="商品库主键ID")
    user_id: str = Field(..., description="用户ID")
    user_content: str = Field("", description="用户指令/调整要求")
    operate_type: str = Field(..., description="操作类型")
    origin_title: str = Field("", description="原始商品标题")
    target_attrs: list[TargetAttr] = Field(
        default_factory=list, description="目标平台属性结构"
    )
    original_attrs: list[OriginAttr] = Field(
        default_factory=list, description="原始属性列表"
    )
    manual_data: ManualData | None = Field(
        None, description="用户手动修改后的数据"
    )


class WarningInfo(BaseModel):
    """警告信息."""
    has_warn: bool = Field(False, description="是否有警告")
    warn_content: str = Field("", description="警告信息")


class SuggestionInfo(BaseModel):
    """建议信息."""
    summary: str = Field("", description="总结建议")
    items: list[str] = Field(default_factory=list, description="建议条目")


class FinalData(BaseModel):
    """最终结构化结果."""
    new_title: str = Field("", description="优化后标题")
    title_note: str = Field("", description="标题优化说明")
    attr_mapping: list[AttrMapping] = Field(
        default_factory=list, description="属性匹配结果"
    )
    warning: WarningInfo = Field(default_factory=WarningInfo)
    suggestion: SuggestionInfo = Field(default_factory=SuggestionInfo)


class StreamMessage(BaseModel):
    """流式中间过程消息."""
    type: str = Field("stream")
    content: str = Field(..., description="模型思考过程文本")


class FinalMessage(BaseModel):
    """最终结构化结果消息."""
    type: str = Field("final")
    data: FinalData = Field(...)


class ConfirmMessage(BaseModel):
    """人工确认消息."""
    type: str = Field("confirm")
    thread_id: str = Field(...)
    import_product_id: str = Field(...)
    user_id: str = Field(...)
    timeout: int = Field(600, description="超时秒数")
    content: str = Field(...)
    data: FinalData = Field(...)


class ErrorMessage(BaseModel):
    """异常消息."""
    type: str = Field("error")
    code: str = Field(...)
    msg: str = Field(...)


class HeartbeatMessage(BaseModel):
    """心跳消息."""
    type: str = Field("heartbeat")
    time: str = Field("")


class ConfirmReplyRequest(BaseModel):
    """客户端回传确认结果."""
    type: str = Field("confirm_reply")
    thread_id: str = Field(..., description="会话唯一标识")
    import_product_id: str = Field(..., description="商品库主键ID")
    user_id: str = Field(..., description="用户ID")
    operate_result: str = Field(..., description="confirm 或 cancel")
    payload: FinalData = Field(..., description="确认携带的完整数据")
