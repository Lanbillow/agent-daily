"""GitHub 镜像数据源（大陆环境）。"""

from __future__ import annotations

from .source import BaseHttpSource


class GitHubMirrorSource(BaseHttpSource):
    """镜像源（地址来自 config，禁止硬编码），返回原始响应。"""

    name = "mirror"
