"""
文件名称：__init__.py
作者：shop-tool
时间：2026-06-15
逻辑说明：Middleware 自动发现，供子 Agent 使用.

discover_middlewares() → create_agent(middleware=...)
"""
import importlib
import logging
import pkgutil
from typing import Any

from app.middlewares.base import BaseMiddleware

logger = logging.getLogger(__name__)

_instances: list[BaseMiddleware] | None = None


def _get_instances() -> list[BaseMiddleware]:
    """懒加载并缓存中间件实例."""
    global _instances
    if _instances is not None:
        return _instances

    _instances = []
    package_dir = __path__  # type: ignore[name-defined]
    for _, name, _ in pkgutil.iter_modules(package_dir):
        if name in ("base",):
            continue
        try:
            module = importlib.import_module(f"{__name__}.{name}")
            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseMiddleware)
                    and obj is not BaseMiddleware
                ):
                    instance = obj()
                    if instance.enabled:
                        _instances.append(instance)
                        logger.info("Middleware loaded: %s", name)
        except Exception:
            logger.exception("Failed to load middleware: %s", name)
    return _instances


def discover_middlewares() -> tuple[Any, ...]:
    """返回用于 create_agent(middleware=...) 的中间件元组."""
    return tuple(_get_instances())
