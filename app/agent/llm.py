"""
文件名称：llm.py
作者：shop-tool
时间：2026-06-14
逻辑说明：多 Provider LLM 工厂，根据配置自动选择模型类.

Provider 分发逻辑：
- OpenAI 兼容 API（DeepSeek / GLM / Qwen / OpenAI / moonshot 等）
  → langchain_openai.ChatOpenAI（通过不同 base_url 切换）
- Anthropic（Opus / Claude）
  → langchain_anthropic.ChatAnthropic（懒加载，未安装则提示）

国内大模型说明：
  多数厂商提供 OpenAI 兼容端点，因此共用 ChatOpenAI 是 LangChain 标准做法。
  区别仅在于 base_url + api_key + model_name 三个参数不同，
  这些参数由用户在 t_shop_llm_config 表中自行配置。

LLM 配置优先从 t_shop_llm_config 读取，无则回退到环境变量。
"""
import logging
from typing import Any

from app.conf.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# 已知的 Anthropic base_url 特征，用于自动检测 Provider
_ANTHROPIC_URL_PATTERNS = ("anthropic.com", "api.anthropic")


def _detect_provider(config: dict[str, Any] | None) -> str:
    """从配置中的 base_url / model_name 自动推断 Provider.

    检测规则：
    - base_url 包含 "anthropic.com" → "anthropic"
    - model_name 以 "claude" 开头 → "anthropic"
    - 其余 → "openai"（OpenAI 兼容 API）
    """
    if config:
        base_url = str(config.get("base_url", ""))
        model_name = str(config.get("model_name", ""))
    else:
        base_url = settings.llm_base_url
        model_name = settings.llm_model_name

    if any(p in base_url for p in _ANTHROPIC_URL_PATTERNS):
        return "anthropic"
    if model_name.lower().startswith("claude"):
        return "anthropic"

    return "openai"


def _build_kwargs(config: dict[str, Any] | None) -> dict[str, Any]:
    """从 config 或 settings 提取 LLM 通用参数."""
    if config:
        return {
            "model": config.get("model_name", settings.llm_model_name),
            "api_key": config.get("api_key", settings.llm_api_key),
            "base_url": config.get("base_url", settings.llm_base_url),
            "temperature": float(config.get("temperature", settings.llm_temperature)),
            "max_tokens": int(config.get("max_tokens", settings.llm_max_tokens)),
            "timeout": int(config.get("timeout_seconds", settings.llm_timeout_seconds)),
            "max_retries": int(config.get("max_retries", settings.llm_max_retries)),
        }
    return {
        "model": settings.llm_model_name,
        "api_key": settings.llm_api_key,
        "base_url": settings.llm_base_url,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
        "timeout": settings.llm_timeout_seconds,
        "max_retries": settings.llm_max_retries,
    }


def create_llm(config: dict[str, Any] | None = None):
    """创建 LLM 实例，根据配置自动选择 Provider 类.

    返回类型为 BaseChatModel（ChatOpenAI 或 ChatAnthropic），
    上层代码无需关心具体是哪个 Provider 类。

    Args:
        config: t_shop_llm_config 中的一行记录，包含
                model_name / api_key / base_url / temperature 等字段
    """
    kwargs = _build_kwargs(config)
    provider = _detect_provider(config)

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(
                "使用 Anthropic Opus/Claude 需要安装 langchain-anthropic: "
                "pip install langchain-anthropic"
            )
        logger.info(
            "Creating Anthropic LLM: model=%s base_url=%s",
            kwargs["model"],
            kwargs.get("base_url", ""),
        )
        # ChatAnthropic 不接受 base_url/max_retries，只传兼容参数
        return ChatAnthropic(
            model=kwargs["model"],
            api_key=kwargs["api_key"],
            temperature=kwargs["temperature"],
            max_tokens=kwargs["max_tokens"],
            timeout=kwargs["timeout"],
        )

    # provider == "openai" — 覆盖所有 OpenAI 兼容 API
    from langchain_openai import ChatOpenAI

    logger.info(
        "Creating OpenAI-compatible LLM: model=%s base_url=%s",
        kwargs["model"],
        kwargs["base_url"],
    )
    return ChatOpenAI(**kwargs)
