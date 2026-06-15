"""
文件名称：sub_agent_builder.py
作者：shop-tool
时间：2026-06-15
逻辑说明：子 Agent 发现与构建，统一注入 middleware.
"""
import importlib
import inspect
import logging
from pathlib import Path
from typing import Any

from app.agent.sub_agents.base import BaseSubAgent

logger = logging.getLogger(__name__)


def discover_sub_agents(llm: Any, middleware: tuple = ()) -> dict[str, Any]:
    """扫描 sub_agents/，创建所有 BaseSubAgent 子类实例的 Agent.

    middleware 统一注入到每个子 Agent（create_agent(middleware=...)）。
    返回 {agent_name: compiled_graph} 字典。
    """
    agents: dict[str, Any] = {}
    pkg_dir = Path(__file__).parent / "sub_agents"

    for f in sorted(pkg_dir.glob("*.py")):
        mod_name = f.stem
        if mod_name.startswith("_") or mod_name == "base":
            continue

        try:
            mod = importlib.import_module(f"app.agent.sub_agents.{mod_name}")
        except Exception:
            logger.exception("子 Agent 模块 %s 导入失败", mod_name)
            continue

        for _name, obj in inspect.getmembers(mod):
            if not isinstance(obj, BaseSubAgent):
                continue
            try:
                agent = obj.create_agent(llm, middleware=middleware)
                agent_key = getattr(agent, "name", mod_name)
                agents[agent_key] = agent
                logger.info("子 Agent 已注册: %s (%s)", agent_key, type(obj).__name__)
            except Exception:
                logger.exception("子 Agent %s.%s 创建失败", mod_name, _name)

    return agents
