"""工具系统：统一接口 + 注册表 + 各工具实现。"""

from .base import Tool, ToolRegistry, ToolResult

__all__ = ["Tool", "ToolResult", "ToolRegistry"]
