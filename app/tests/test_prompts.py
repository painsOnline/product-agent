"""
文件名称：test_prompts.py
作者：shop-tool
时间：2026-06-14
逻辑说明：提示词加载单元测试.
"""
import pytest

from app.agent.prompts import (
    PromptLoader,
    get_supervisor_prompt,
    get_title_optimizer_prompt,
    get_attribute_matcher_prompt,
)


class TestPromptLoader:
    """PromptLoader 测试."""

    def test_get_known_prompts(self) -> None:
        loader = PromptLoader()
        supervisor = loader.get("supervisor_prompt")
        assert len(supervisor) > 0

    def test_get_missing_prompt_returns_default(self) -> None:
        loader = PromptLoader()
        result = loader.get("no_such_prompt", "default_value")
        assert result == "default_value"

    def test_reload(self) -> None:
        loader = PromptLoader()
        loader.get("supervisor_prompt")  # populate cache
        loader.reload()
        # cache cleared, next get will re-read


class TestPromptFunctions:
    """模块级提示词函数."""

    def test_get_supervisor_prompt(self) -> None:
        prompt = get_supervisor_prompt()
        assert len(prompt) > 0

    def test_get_title_optimizer_prompt(self) -> None:
        prompt = get_title_optimizer_prompt()
        assert len(prompt) > 0

    def test_get_attribute_matcher_prompt(self) -> None:
        prompt = get_attribute_matcher_prompt()
        assert len(prompt) > 0
