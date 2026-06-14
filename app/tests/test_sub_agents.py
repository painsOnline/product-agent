"""
文件名称：test_sub_agents.py
作者：shop-tool
时间：2026-06-14
逻辑说明：子 Agent 创建和注册表单元测试.
"""
import pytest

from app.agent.sub_agents import get_registry
from app.agent.sub_agent_builder import SubAgentBuilder


class TestSubAgentRegistry:
    """子 Agent 注册表."""

    def test_registry_not_empty(self) -> None:
        factories = get_registry()
        assert len(factories) >= 2

    def test_registry_factories_are_callable(self) -> None:
        for factory in get_registry():
            assert callable(factory)


class TestSubAgentBuilder:
    """SubAgentBuilder 批量构建."""

    def test_build_all_returns_list(self) -> None:
        builder = SubAgentBuilder(llm_config={
            "model_name": "test-model", "api_key": "sk-test",
            "base_url": "http://localhost", "temperature": 0.0,
            "max_tokens": 10, "timeout_seconds": 5, "max_retries": 0,
        })
        agents = builder.build_all()
        assert len(agents) >= 2
        for agent in agents:
            # DeepAgents SubAgent uses dict-like structure
            assert isinstance(agent, dict) or hasattr(agent, "name")

    def test_build_all_with_default_config(self) -> None:
        builder = SubAgentBuilder()
        agents = builder.build_all()
        assert len(agents) >= 2
