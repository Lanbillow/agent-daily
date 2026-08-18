"""github_trending 工具：采集 GitHub 热门项目（Source Adapter 切换数据源）。

目录职责：
  models.py   Repo 数据模型
  source.py   数据源协议 + SourceAdapter + HTTP 基类 + GithubSourceError
  official.py GitHub 官方源
  mirror.py   镜像源
  parser.py   HTML/JSON → Repo[] + GithubParseError
  tool.py     对外 Tool.run(args) → ToolResult
"""

from .models import Repo
from .parser import GithubParseError, parse, parse_html, parse_json
from .source import (
    BaseHttpSource,
    GithubSourceError,
    SourceAdapter,
    TrendingSource,
)
from .tool import GithubTrendingTool

__all__ = [
    "Repo",
    "GithubSourceError",
    "GithubParseError",
    "TrendingSource",
    "BaseHttpSource",
    "SourceAdapter",
    "GithubTrendingTool",
    "parse",
    "parse_html",
    "parse_json",
]
