"""运行历史/状态存储（data/state/job_runs.jsonl）。

每条记录一次任务运行，字段：job / status / start_time / end_time / artifacts。
为未来 UI 的「任务列表 / 系统运行状态」提供数据基础。追加写、不覆盖。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(dt_timezone.utc).isoformat()


class StateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def log_run(
        self,
        job: str,
        status: str,
        start_time: str | None = None,
        end_time: str | None = None,
        artifacts: list[Any] | None = None,
        **meta: Any,
    ) -> None:
        """追加一条运行记录。start_time / end_time 缺省时取当前 UTC 时间。"""
        record: dict[str, Any] = {
            "job": job,
            "status": status,
            "start_time": start_time or _now_iso(),
            "end_time": end_time or _now_iso(),
            "artifacts": artifacts or [],
        }
        record.update(meta)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def history(self) -> list[dict[str, Any]]:
        """读取全部运行记录（写入顺序）。"""
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records
