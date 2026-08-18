"""网页抓取/信息收集工具（第二阶段实现，Phase 0 仅冻结接口桩）。"""

from __future__ import annotations

from typing import Any

from .base import ToolResult


class FetchUrlTool:
    name = "fetch_url"
    description = "抓取网页并抽取正文"
    parameters = {"type": "object", "properties": {"url": {"type": "string"}}}

    def run(self, args: dict[str, Any]) -> ToolResult:
        raise NotImplementedError("FetchUrlTool.run 将在第二阶段实现")
