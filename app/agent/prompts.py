"""
文件名称：prompts.py
作者：shop-tool
时间：2026-06-14
逻辑说明：加载 YAML 提示词配置文件，路径可注入（OCP）.

PromptLoader 类封装加载与缓存，默认路径保持向后兼容。
"""
import logging
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)


class PromptLoader:
    """从 YAML 加载提示词，支持可注入路径和缓存."""

    def __init__(self, prompts_path: str | None = None) -> None:
        """初始化提示词加载器.

        Args:
            prompts_path: YAML 文件路径，默认取项目 prompts/prompts.yml
        """
        self._path = prompts_path or str(
            Path(__file__).parent.parent / "prompts" / "prompts.yml"
        )
        self._cache: dict | None = None

    def get(self, name: str, default: str = "") -> str:
        """获取指定名称的提示词.

        Args:
            name: 提示词名称（如 supervisor_prompt）
            default: 未找到时的默认值

        Returns:
            提示词文本
        """
        if self._cache is None:
            self._cache = self._load()
        return self._cache.get(name, default)

    def _load(self) -> dict:
        """从 YAML 文件加载全部提示词."""
        if yaml is None:
            logger.warning("PyYAML not installed, using empty prompts")
            return {}
        if not Path(self._path).exists():
            logger.warning("Prompts file not found at %s", self._path)
            return {}
        with open(self._path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def reload(self) -> None:
        """清除缓存，下次访问时重新加载."""
        self._cache = None


# 全局默认实例，保持现有 API 兼容
_default_loader = PromptLoader()


def get_prompt(name: str, default: str = "") -> str:
    """获取指定名称的提示词（模块级便捷函数）."""
    return _default_loader.get(name, default)


def get_supervisor_prompt() -> str:
    """获取 Supervisor Agent 提示词."""
    return get_prompt("supervisor_prompt", "")


def get_title_optimizer_prompt() -> str:
    """获取 Title Optimizer Agent 提示词."""
    return get_prompt("title_optimizer_prompt", "")


def get_attribute_matcher_prompt() -> str:
    """获取 Attribute Matcher Agent 提示词."""
    return get_prompt("attribute_matcher_prompt", "")
