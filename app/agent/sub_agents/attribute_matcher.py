"""
文件名称：attribute_matcher.py
作者：shop-tool
时间：2026-06-14
逻辑说明：Attribute Matcher 子 Agent 创建模块（SRP：只负责本 Agent 的构造）.

新增 Agent 时参考此文件：实现 create_sub_agent(llm_config) -> SubAgent 即可.
"""
from typing import Any

from deepagents.middleware.subagents import SubAgent

from app.agent.llm import create_llm
from app.agent.prompts import get_attribute_matcher_prompt


def create_sub_agent(llm_config: dict[str, Any] | None = None) -> SubAgent:
    """创建属性匹配子 Agent."""
    return SubAgent(
        name="attribute-matcher",
        description=(
            "将1688/淘宝源属性映射到街顺目标平台属性，"
            "生成映射表+警告+建议"
        ),
        system_prompt=get_attribute_matcher_prompt(),
        model=create_llm(llm_config),
    )
