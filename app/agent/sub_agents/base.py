"""
文件名称：base.py
作者：shop-tool
时间：2026-06-15
逻辑说明：子 Agent 基类，所有子 Agent 继承并实现 create_agent(llm, pre_model_hook).
"""
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class BaseSubAgent(ABC):
    """子 Agent 抽象基类.

    所有 sub_agents/ 下的模块必须继承并导出实例。
    pre_model_hook 由上层注入（上下文压缩等中间件）。
    """

    @abstractmethod
    def create_agent(
        self,
        llm: Any,
        pre_model_hook: Callable | None = None,
    ) -> Any:
        """创建子 Agent 的 CompiledStateGraph.

        Args:
            llm: LangChain 聊天模型
            pre_model_hook: 可选，主管传递的组合钩子（上下文压缩等）
        """
        ...
