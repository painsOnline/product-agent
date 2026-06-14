"""
文件名称：title_optimizer.py
作者：shop-tool
时间：2026-06-14
逻辑说明：Title Optimizer 子 Agent 创建模块（SRP：只负责本 Agent 的构造）.

新增 Agent 时参考此文件：实现 create_sub_agent(llm_config) -> SubAgent 即可.
"""
from typing import Any

from deepagents.middleware.subagents import SubAgent

from app.agent.llm import create_llm
from app.agent.prompts import get_title_optimizer_prompt


def create_sub_agent(llm_config: dict[str, Any] | None = None) -> SubAgent:
    """创建标题优化子 Agent."""
    return SubAgent(
        name="title-optimizer",
        description=(
            "商品标题优化，遵循品牌+品名+名称+规格命名规则，"
            "去除营销词汇，max 45字符"
        ),
        system_prompt=get_title_optimizer_prompt(),
        model=create_llm(llm_config),
    )
