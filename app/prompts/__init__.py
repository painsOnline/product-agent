"""
文件名称：__init__.py
作者：shop-tool
时间：2026-06-15
逻辑说明：提示词统一入口 — YAML 加载 + 静态获取 + 动态构建.

所有提示词相关职责在此目录：
- prompts.yml          — 固定提示词模板
- __init__.py          — PromptLoader / get_* / build_* 函数
"""
import json as _json
import logging
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

_JSON_SUFFIX = "\n请输出 json 格式结果。"


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


def get_supervisor_prompt() -> str:
    return get_prompt("supervisor_prompt", "")


def get_title_optimizer_prompt() -> str:
    return get_prompt("title_optimizer_prompt", "")


def get_attribute_matcher_prompt() -> str:
    return get_prompt("attribute_matcher_prompt", "")


def get_intent_prompt() -> str:
    return get_prompt("intent_prompt", "")


# ==================== 动态 Prompt 构建（state → str） ====================

def build_supervisor_prompt(state: dict[str, Any]) -> str:
    """主管 prompt，注入 state 中的业务数据."""
    parts = [get_supervisor_prompt()]
    parts.append(f"\n[operate_type={state.get('operate_type', 'both')}]")
    if state.get("user_content"):
        parts.append(f"用户要求: {state['user_content']}")
    if state.get("original_title"):
        parts.append(f"原始标题: {state['original_title']}")
    previous = state.get("latest_result")
    if previous:
        parts.append(f"\n上一轮结果: {_json.dumps(previous, ensure_ascii=False)}")
    parts.append(_JSON_SUFFIX)
    return "\n".join(parts)


def build_title_optimizer_prompt(state: dict[str, Any]) -> str:
    """标题优化子 Agent prompt."""
    parts = [get_title_optimizer_prompt()]
    parts.append(f"\n原始标题: {state.get('original_title', '')}")
    parts.append(f"用户要求: {state.get('user_content', '按标准规则优化')}")
    if state.get("ban_words"):
        parts.append(f"禁用词: {state['ban_words']}")
    parts.append(f"最大长度: {state.get('title_max_len', 45)}字符")
    parts.append(_JSON_SUFFIX)
    return "\n".join(parts)


def build_attribute_matcher_prompt(state: dict[str, Any]) -> str:
    """属性匹配子 Agent prompt."""
    parts = [get_attribute_matcher_prompt()]
    original_attrs = state.get("original_attrs", [])
    target_attrs = state.get("target_attrs", [])
    if original_attrs:
        parts.append(f"\n源属性: {_json.dumps(original_attrs, ensure_ascii=False)}")
    if target_attrs:
        parts.append(f"目标属性: {_json.dumps(target_attrs, ensure_ascii=False)}")
    parts.append(_JSON_SUFFIX)
    return "\n".join(parts)
