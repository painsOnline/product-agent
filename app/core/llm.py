"""
文件名称：llm.py
作者：shop-tool
时间：2026-06-15
逻辑说明：多 Provider LLM 工厂，配置必须从 t_shop_llm_config 表中获取.

DeepSeek 特殊处理：开启 response_format json_object 后，所有 function tools
必须带 strict: true。deepagents 内置 write_todos 默认不带，此处 monkey-patch
ChatDeepSeek._get_request_payload 统一补齐。
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

_ANTHROPIC_URL_PATTERNS = ("anthropic.com", "api.anthropic")
_DEEPSEEK_PATCHED = False


def _patch_deepseek_strict_tools():
    """Monkey-patch ChatDeepSeek，让所有 tools 强制 strict: true."""
    global _DEEPSEEK_PATCHED
    if _DEEPSEEK_PATCHED:
        return
    from langchain_deepseek import ChatDeepSeek

    _orig = ChatDeepSeek._get_request_payload

    def _patched(self, input_, *, stop=None, **kwargs):
        payload = _orig(self, input_, stop=stop, **kwargs)
        tools = payload.get("tools")
        if tools:
            for tool in tools:
                if "function" in tool:
                    tool["function"]["strict"] = True
        return payload

    ChatDeepSeek._get_request_payload = _patched
    _DEEPSEEK_PATCHED = True
    logger.info("ChatDeepSeek._get_request_payload patched: strict:true on all tools")


def create_llm(config: dict[str, Any]):
    """创建 LLM 实例.

    Args:
        config: t_shop_llm_config 表的一行（已转为 dict），必填字段:
                provider / api_key / model_name / base_url
    """
    provider = config.get("provider", "")
    model = config.get("model_name", "")
    base_url = config.get("base_url", "")

    if not provider:
        raise ValueError("LLM 配置缺少 provider 字段")
    if not config.get("api_key"):
        raise ValueError("LLM 配置缺少 api_key，请在 t_shop_llm_config 表中配置")

    if (
        provider == "anthropic"
        or any(p in base_url for p in _ANTHROPIC_URL_PATTERNS)
        or model.lower().startswith("claude")
    ):
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(
                "使用 Anthropic 需要安装 langchain-anthropic"
            )
        logger.info("Creating Anthropic LLM: model=%s", model)
        return ChatAnthropic(
            model=model,
            api_key=config["api_key"],
            temperature=float(config.get("temperature", 0.3)),
            max_tokens=int(config.get("max_tokens", 4096)),
            timeout=int(config.get("timeout_seconds", 60)),
        )

    _IS_DEEPSEEK = (
        provider == "deepseek"
        or model.lower().startswith("deepseek")
        or "deepseek" in base_url
    )

    if _IS_DEEPSEEK:
        from langchain_deepseek import ChatDeepSeek

        _patch_deepseek_strict_tools()
        logger.info("Creating DeepSeek LLM: model=%s", model)
        return ChatDeepSeek(
            model=model,
            api_key=config["api_key"],
            api_base=base_url,
            temperature=float(config.get("temperature", 0.3)),
            max_tokens=int(config.get("max_tokens", 4096)),
            timeout=int(config.get("timeout_seconds", 60)),
            max_retries=int(config.get("max_retries", 3)),
        )

    from langchain_openai import ChatOpenAI

    logger.info("Creating OpenAI-compatible LLM: model=%s base_url=%s", model, base_url)
    return ChatOpenAI(
        model=model,
        api_key=config["api_key"],
        base_url=base_url,
        temperature=float(config.get("temperature", 0.3)),
        max_tokens=int(config.get("max_tokens", 4096)),
        timeout=int(config.get("timeout_seconds", 60)),
        max_retries=int(config.get("max_retries", 3)),
    )
