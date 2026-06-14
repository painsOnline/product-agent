"""
文件名称：conftest.py
作者：shop-tool
时间：2026-06-14
逻辑说明：pytest 全局配置和 fixtures.
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环供测试使用."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
