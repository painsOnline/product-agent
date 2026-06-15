"""
文件名称：test_llm.py
作者：shop-tool
时间：2026-06-14
逻辑说明：LLM 工厂和 Provider 检测单元测试.
"""
import pytest

from app.core.llm import create_llm


class TestProviderDetection:
    """Provider 自动检测."""

    def test_detect_openai_default(self) -> None:
        assert _detect_provider(None) == "openai"

    def test_detect_anthropic_by_url(self) -> None:
        config = {"base_url": "https://api.anthropic.com"}
        assert _detect_provider(config) == "anthropic"

    def test_detect_anthropic_by_model(self) -> None:
        config = {"model_name": "claude-opus-4-7"}
        assert _detect_provider(config) == "anthropic"

    def test_detect_deepseek_as_openai(self) -> None:
        config = {"base_url": "https://api.deepseek.com/v1"}
        assert _detect_provider(config) == "openai"


class TestBuildKwargs:
    """LLM 参数构建."""

    def test_build_from_config(self) -> None:
        config = {
            "model_name": "deepseek-chat",
            "api_key": "sk-xxx",
            "base_url": "https://api.deepseek.com/v1",
            "temperature": 0.5,
            "max_tokens": 4096,
            "timeout_seconds": 30,
            "max_retries": 2,
        }
        kwargs = _build_kwargs(config)
        assert kwargs["model"] == "deepseek-chat"
        assert kwargs["temperature"] == 0.5

    def test_build_from_defaults(self) -> None:
        kwargs = _build_kwargs(None)
        assert "model" in kwargs
        assert "api_key" in kwargs
        assert "base_url" in kwargs


class TestCreateLLM:
    """LLM 实例创建."""

    def test_create_openai_llm(self) -> None:
        config = {"model_name": "deepseek-chat", "api_key": "sk-xxx",
                  "base_url": "https://api.deepseek.com/v1",
                  "temperature": 0.5, "max_tokens": 100,
                  "timeout_seconds": 10, "max_retries": 1}
        llm = create_llm(config)
        assert llm is not None
        assert llm.model_name == "deepseek-chat"

    def test_create_with_defaults(self) -> None:
        llm = create_llm(None)
        assert llm is not None
