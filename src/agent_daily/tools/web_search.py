"""Web 搜索工具（第二阶段实现，Phase 0 仅冻结接口桩）。"""

from __future__ import annotations

from typing import Any

from .base import ToolResult


class WebSearchTool:
    name = "web_search"
    description = "搜索网页并返回结果"
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}}

    def run(self, args: dict[str, Any]) -> ToolResult:
        raise NotImplementedError("WebSearchTool.run 将在第二阶段实现")
