"""
子 Agent 注册表.

新增 Agent 步骤（OCP：只扩展不修改）：
1. 新建 sub_agents/new_agent.py，实现 create_sub_agent(llm_config) -> SubAgent
2. 在此文件底部追加一行 import 注册

SubAgentBuilder 通过 _REGISTRY 发现所有子 Agent，无需了解具体实现.
"""
from collections.abc import Callable
from typing import Any

from deepagents.middleware.subagents import SubAgent

from app.agent.sub_agents.attribute_matcher import create_sub_agent as _attr_matcher
from app.agent.sub_agents.title_optimizer import create_sub_agent as _title_opt

# 子 Agent 工厂函数注册表
# 类型: list[Callable[[dict | None], SubAgent]]
_REGISTRY: list[Callable[..., SubAgent]] = [
    _title_opt,
    _attr_matcher,
]


def get_registry() -> list[Callable[..., SubAgent]]:
    """获取已注册的子 Agent 工厂函数列表."""
    return list(_REGISTRY)
