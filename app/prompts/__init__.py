"""
文件名称：__init__.py
作者：shop-tool
时间：2026-06-15
逻辑说明：提示词统一入口 — YAML 加载 + 静态获取 + 动态构建.

所有提示词相关职责在此目录：
- prompts.yml          — 固定提示词模板
- __init__.py          — PromptLoader / get_* / build_* 函数
"""
import logging
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)


# ==================== YAML 加载器 ====================

class PromptLoader:
    """从 YAML 加载提示词，支持可注入路径和缓存."""

    def __init__(self, prompts_path: str | None = None) -> None:
        self._path = prompts_path or str(Path(__file__).parent / "prompts.yml")
        self._cache: dict | None = None

    def get(self, name: str, default: str = "") -> str:
        if self._cache is None:
            self._cache = self._load()
        return self._cache.get(name, default)

    def _load(self) -> dict:
        if yaml is None:
            logger.warning("PyYAML not installed, using empty prompts")
            return {}
        if not Path(self._path).exists():
            logger.warning("Prompts file not found at %s", self._path)
            return {}
        with open(self._path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def reload(self) -> None:
        self._cache = None


_default_loader = PromptLoader()


# ==================== 静态 Prompt 获取 ====================

def get_prompt(name: str, default: str = "") -> str:
    return _default_loader.get(name, default)


def get_title_optimizer_prompt() -> str:
    return get_prompt("title_optimizer_prompt", "")


def get_attribute_matcher_prompt() -> str:
    return get_prompt("attribute_matcher_prompt", "")


def get_intent_prompt() -> str:
    return get_prompt("intent_prompt", "")
