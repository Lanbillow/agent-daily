"""LocalFileProvider —— 本地文件输出（离线/测试/fallback）。

title + content 写入 Markdown 文件；文件名由 title 派生，同名覆盖（天然幂等）。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import OutputError


def _slug(title: str) -> str:
    """把 title 转成安全的文件名片段。"""
    slug = re.sub(r'[\\/:*?"<>|\s]+', "-", title).strip("-")
    return slug or "output"


class LocalFileProvider:
    name = "local_file"

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def write(self, title: str, content: str, **kwargs: Any) -> Path:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path = self.output_dir / f"{_slug(title)}.md"
            path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
        except OSError as exc:
            raise OutputError(f"本地文件写入失败：{exc}") from exc
        return path
