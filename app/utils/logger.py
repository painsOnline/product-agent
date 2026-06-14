"""
文件名称：logger.py
作者：shop-tool
时间：2026-06-14
逻辑说明：结构化日志设置，统一日志格式.
"""
import logging
import sys


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """设置并返回结构化日志记录器."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
