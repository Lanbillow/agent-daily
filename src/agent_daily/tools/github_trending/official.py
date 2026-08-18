"""GitHub 官方数据源。"""

from __future__ import annotations

from .source import BaseHttpSource


class GitHubOfficialSource(BaseHttpSource):
    """GitHub 官方热榜数据源（地址来自 config），返回原始 HTML。"""

    name = "official"
