"""Artifact 机制 —— 任务间唯一的数据通道。

禁止任务之间直接内存调用：所有跨任务数据通过命名 Artifact 落盘传递。

路径约定：``data/processed/{YYYY-MM-DD}/{name}.{ext}``，日期按配置时区
（默认 UTC+8）分区。支持类型：json / markdown / text。

每个 Artifact 落盘两份文件：
  - 内容文件：``{name}.{ext}``
  - 元数据文件：``.meta/{name}.{ext}``（JSON：name / type / created_at / metadata）

元数据独立侧车，保证 launchd 独立进程之间也能读到 created_at / metadata，
且不会被 ``*.json`` 之类的内容匹配误抓。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

# 类型 → 文件扩展名
_TYPE_EXTENSIONS = {"json": ".json", "markdown": ".md", "text": ".txt"}
SUPPORTED_TYPES = tuple(_TYPE_EXTENSIONS)


def _now_iso() -> str:
    return datetime.now(dt_timezone.utc).isoformat()


@dataclass
class ArtifactSpec:
    """工件契约（S7 job YAML 的 inputs/outputs 声明用）。"""

    name: str
    type: str
    path: str = ""  # 相对 storage 根；留空则按默认规则派生


@dataclass
class Artifact:
    """一个具名工件。"""

    name: str
    type: str
    path: Path
    created_at: str
    metadata: dict = field(default_factory=dict)
    data: Any = None


class ArtifactStore:
    def __init__(self, root: str | Path, timezone: str = "Asia/Shanghai") -> None:
        self.root = Path(root)
        self.timezone = timezone

    # -- helpers ---------------------------------------------------------
    def _validate_type(self, type_: str) -> None:
        if type_ not in _TYPE_EXTENSIONS:
            raise ValueError(
                f"不支持的 Artifact 类型：{type_!r}（支持 {list(_TYPE_EXTENSIONS)}）"
            )

    def _extension(self, type_: str) -> str:
        self._validate_type(type_)
        return _TYPE_EXTENSIONS[type_]

    def _date_str(self, date: str | None) -> str:
        if date:
            return date
        return datetime.now(ZoneInfo(self.timezone)).strftime("%Y-%m-%d")

    def resolve_path(self, name: str, type_: str, date: str | None = None) -> Path:
        return self.root / self._date_str(date) / f"{name}{self._extension(type_)}"

    def _meta_path(self, path: Path) -> Path:
        return path.parent / ".meta" / path.name

    # -- serialization ---------------------------------------------------
    def _serialize(self, type_: str, data: Any) -> str:
        if type_ == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        return str(data)

    def _deserialize(self, type_: str, text: str) -> Any:
        if type_ == "json":
            return json.loads(text)
        return text

    # -- public API ------------------------------------------------------
    def save(
        self,
        name: str,
        type_: str,
        data: Any,
        date: str | None = None,
        metadata: dict | None = None,
    ) -> Artifact:
        """写入工件，返回带 created_at / metadata 的 Artifact。"""
        self._validate_type(type_)
        path = self.resolve_path(name, type_, date)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._serialize(type_, data), encoding="utf-8")

        created_at = _now_iso()
        meta = {
            "name": name,
            "type": type_,
            "created_at": created_at,
            "metadata": metadata or {},
        }
        meta_path = self._meta_path(path)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return Artifact(
            name=name,
            type=type_,
            path=path,
            created_at=created_at,
            metadata=metadata or {},
            data=data,
        )

    def load(self, name: str, type_: str, date: str | None = None) -> Any:
        """读取工件内容（按类型反序列化）。"""
        self._validate_type(type_)
        path = self.resolve_path(name, type_, date)
        if not path.exists():
            raise FileNotFoundError(f"Artifact 不存在：{path}")
        return self._deserialize(type_, path.read_text(encoding="utf-8"))

    def exists(self, name: str, type_: str, date: str | None = None) -> bool:
        self._validate_type(type_)
        return self.resolve_path(name, type_, date).exists()

    def load_metadata(self, name: str, type_: str, date: str | None = None) -> dict:
        """读取工件元数据（sidecar）。"""
        self._validate_type(type_)
        meta_path = self._meta_path(self.resolve_path(name, type_, date))
        if not meta_path.exists():
            raise FileNotFoundError(f"Artifact 元数据不存在：{meta_path}")
        return json.loads(meta_path.read_text(encoding="utf-8"))
