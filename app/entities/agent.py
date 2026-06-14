"""
文件名称：agent.py
作者：shop-tool
时间：2026-06-14
逻辑说明：Agent 结构化输出实体定义.

TitleOptimizerOutput: 子 Agent 标题优化输出（与 prompts.yml 约束对齐）
AttributeMatcherOutput: 子 Agent 属性匹配输出（与 prompts.yml 约束对齐）
SupervisorOutput: 主 Agent 最终输出（与 llm_schema.md 对齐）

使用 LangChain 原生 with_structured_output() + Pydantic 做 Schema 校验.
"""
from pydantic import BaseModel, Field

from app.entities.chat import AttrMapping


class TitleOptimizerOutput(BaseModel):
    """标题优化子 Agent 结构化输出."""
    new_title: str = Field(..., description="优化后标题")
    title_note: str = Field(..., description="标题优化说明")
    warning: dict = Field(default_factory=dict)
    suggestion: dict = Field(default_factory=dict)


class AttributeMatcherOutput(BaseModel):
    """属性匹配子 Agent 结构化输出."""
    attr_mapping: list[AttrMapping] = Field(
        default_factory=list, description="属性匹配结果"
    )
    warning: dict = Field(default_factory=dict)
    suggestion: dict = Field(default_factory=dict)


class SupervisorOutput(BaseModel):
    """主 Agent 最终结构化输出（与 llm_schema.md 完全对齐）."""
    new_title: str = Field("", description="优化后标题")
    title_note: str = Field("", description="标题优化说明")
    import_product_id: str = Field("", description="商品ID")
    thread_id: str = Field("", description="会话ID")
    user_id: str = Field("", description="用户ID")
    attr_mapping: list[AttrMapping] = Field(
        default_factory=list, description="属性匹配结果"
    )
    warning: dict = Field(default_factory=dict)
    suggestion: dict = Field(default_factory=dict)
