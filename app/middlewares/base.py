"""
文件名称：base.py
作者：shop-tool
时间：2026-06-14
逻辑说明：中间件基类.

新增 Middleware 步骤（OCP：只加文件不改旧代码）：
1. 在 app/middlewares/ 下新建 xxx.py
2. 继承 BaseMiddleware，实现回调方法
3. 完成，自动被 discover_middlewares() 发现加载

所有 Middleware 通过 RequestContext.current() 获取依赖，
无需外部传参，消除构造函数耦合.
"""
from langchain_core.callbacks.base import BaseCallbackHandler


class BaseMiddleware(BaseCallbackHandler):
    """Middleware 基类，兼容 create_deep_agent(callbacks=[...])."""

    # 子类可设为 True 禁用此中间件
    enabled: bool = True
