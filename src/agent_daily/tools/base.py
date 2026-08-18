"""工具系统统一接口与注册表。

工具不依赖 model / agent，是独立能力单元。每个工具暴露 name / description /
parameters（JSON Schema），供上层（未来自主 Agent）生成调用；Phase 1 由
workflow 的 tool 步骤直接按 name 调用。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None


class Tool(Protocol):
    """工具协议。"""

    name: str
    description: str
    parameters: dict  # JSON Schema

    def run(self, args: dict[str, Any]) -> ToolResult:
        """执行工具，返回结构化结果。"""
        ...


class ToolRegistry:
    """工具注册表（容器，Phase 0 即可用）。"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"未注册的工具：{name}")
        return self._tools[name]

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return list(self._tools.keys())
