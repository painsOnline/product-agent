"""
文件名称：__init__.py
作者：shop-tool
时间：2026-06-14
逻辑说明：Middleware 自动发现，扫描本目录下继承 BaseMiddleware 的类并实例化.

新增 Middleware 只需两步（OCP）：
1. 在本目录新建 xxx.py，继承 BaseMiddleware
2. 无需其他改动，自动被 discover_middlewares() 发现
"""
import importlib
import logging
import pkgutil
from collections.abc import Iterable

from app.middlewares.base import BaseMiddleware

logger = logging.getLogger(__name__)


def discover_middlewares() -> list[BaseMiddleware]:
    """自动发现并实例化所有 Middleware.

    扫描 app/middlewares/ 目录，跳过 __init__.py 和 base.py。
    """
    instances: list[BaseMiddleware] = []
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
                        instances.append(instance)
                        logger.info("Middleware loaded: %s", name)
        except Exception:
            logger.exception("Failed to load middleware: %s", name)

    return instances
