"""github_trending 工具：采集 GitHub 热门项目。

流程：SourceAdapter 选源 → Source.fetch 取原始响应 → Parser 转 Repo[]。
失败时 Source/Parser 抛明确异常（GithubSourceError / GithubParseError），
本工具不吞异常，直接向上传播。
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..base import ToolResult
from .parser import parse
from .source import SourceAdapter


class GithubTrendingTool:
    name = "github_trending"
    description = "采集 GitHub 热门项目列表（返回结构化 Repo 列表）"
    parameters = {
        "type": "object",
        "properties": {
            "since": {"type": "string", "enum": ["daily", "weekly", "monthly"]},
            "limit": {"type": "integer", "default": 10},
        },
    }

    def __init__(self, adapter: SourceAdapter) -> None:
        self.adapter = adapter

    def run(self, args: dict[str, Any]) -> ToolResult:
        since = str(args.get("since", "daily"))
        limit = int(args.get("limit", 10))

        source = self.adapter.get_source()          # 失败抛 GithubSourceError
        raw = source.fetch(since=since)             # 失败抛 GithubSourceError
        repos = parse(source.format, raw, base_url=source.base_url)  # 失败抛 GithubParseError

        data = [asdict(r) for r in repos[:limit]]
        return ToolResult(success=True, data=data)
