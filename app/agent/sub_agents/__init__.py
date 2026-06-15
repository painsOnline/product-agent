"""
子 Agent 包.

新增子 Agent 步骤（OCP，只扩展不修改）：
1. 新建 sub_agents/new_agent.py
2. 定义 class NewAgent(BaseSubAgent)，实现 create_agent(self, llm) 方法
3. 在模块顶层创建实例：new_agent = NewAgent()
4. sub_agent_builder.discover_sub_agents() 通过 isinstance 自动发现
"""
from app.agent.sub_agents.base import BaseSubAgent

__all__ = ["BaseSubAgent"]
