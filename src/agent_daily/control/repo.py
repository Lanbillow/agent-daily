"""Control Plane 只读数据仓储（文件即真相）。

只读访问 v0.1.0 的共享数据文件：
  jobs/*.yaml、config.yaml、data/state/job_runs.jsonl、
  data/processed/、data/logs/、scheduler 状态、model 配置。

约束：本模块只 import 只读/校验模块（config / storage.state / scheduler），
绝不 import 执行模块（agent/tools/model/output/jobs.runner）。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from ..config.loader import PROJECT_ROOT, load_config, load_secrets
from ..storage.state import StateStore

_EXT_TO_TYPE = {".json": "json", ".md": "markdown", ".txt": "text"}


class Repo:
    def __init__(self, project_root: str | Path | None = None) -> None:
        self.root = Path(project_root) if project_root else PROJECT_ROOT
        self.jobs_dir = self.root / "jobs"
        self.config_dir = self.root / "config"
        self.data_dir = self.root / "data"

    # -- 基础 ---------------------------------------------------------
    def _settings(self) -> Any:
        return load_config(self.config_dir / "config.yaml")

    def _secrets(self) -> dict[str, str]:
        return load_secrets(self.config_dir / "secrets.env")

    def _state_path(self) -> Path:
        return self.data_dir / "state" / "job_runs.jsonl"

    def _processed_dir(self) -> Path:
        return self.root / self._settings().storage.processed_dir

    def _logs_dir(self) -> Path:
        return self.root / self._settings().logging.dir

    # -- jobs ---------------------------------------------------------
    def read_jobs(self) -> list[dict]:
        last_status = self._last_status_map()
        jobs = []
        if not self.jobs_dir.exists():
            return jobs
        for path in sorted(self.jobs_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                data = {}
            if not isinstance(data, dict):
                data = {}
            job_id = data.get("job") or path.stem
            jobs.append({
                "id": job_id,
                "schedule": data.get("schedule", ""),
                "description": data.get("description", ""),
                "enabled": data.get("enabled", True),
                "last_status": last_status.get(job_id),
            })
        return jobs

    def _last_status_map(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for rec in StateStore(self._state_path()).history():
            if rec.get("job"):
                result[str(rec["job"])] = str(rec.get("status", ""))
        return result

    # -- runs ---------------------------------------------------------
    def read_runs(self, limit: int = 50, offset: int = 0, job: str | None = None) -> dict:
        history = StateStore(self._state_path()).history()
        if job:
            history = [r for r in history if r.get("job") == job]
        history = list(reversed(history))  # 最新在前
        total = len(history)
        return {"total": total, "items": history[offset:offset + limit]}

    # -- artifacts ----------------------------------------------------
    def read_artifacts(self, date: str | None = None) -> dict:
        root = self._processed_dir()
        dates = []
        artifacts: list[dict] = []
        if root.exists():
            dates = sorted(
                d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")
            )
            if date is not None:
                artifacts = self._list_artifacts(root / date, date)
        return {"dates": dates, "artifacts": artifacts}

    def _list_artifacts(self, date_dir: Path, date: str) -> list[dict]:
        result = []
        if not date_dir.exists():
            return result
        for f in sorted(date_dir.iterdir()):
            if f.is_dir() or f.name.startswith("."):
                continue
            type_ = _EXT_TO_TYPE.get(f.suffix)
            if type_ is None:
                continue
            meta = self._read_meta(date_dir, f.name)
            result.append({
                "name": f.stem,
                "type": type_,
                "date": date,
                "path": str(f),
                "created_at": (meta or {}).get("created_at"),
            })
        return result

    def _read_meta(self, date_dir: Path, filename: str) -> dict | None:
        meta_path = date_dir / ".meta" / filename
        if not meta_path.exists():
            return None
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    def read_artifact(self, date: str, name: str) -> dict:
        date_dir = self._processed_dir() / date
        for f in date_dir.iterdir():
            if f.is_file() and f.stem == name and f.suffix in _EXT_TO_TYPE:
                type_ = _EXT_TO_TYPE[f.suffix]
                content: Any = f.read_text(encoding="utf-8")
                if type_ == "json":
                    content = json.loads(content)
                return {"name": name, "type": type_, "date": date, "content": content}
        raise FileNotFoundError(f"artifact {name!r} @ {date!r}")

    # -- config -------------------------------------------------------
    def read_config(self) -> dict:
        secrets = self._secrets()
        return {
            "config": asdict(self._settings()),
            "secrets": {
                "DEEPSEEK_API_KEY": bool(secrets.get("DEEPSEEK_API_KEY")),
                "FEISHU_APP_ID": bool(secrets.get("FEISHU_APP_ID")),
                "FEISHU_APP_SECRET": bool(secrets.get("FEISHU_APP_SECRET")),
            },
        }

    # -- models（只读）-------------------------------------------------
    def read_models(self) -> list[dict]:
        settings = self._settings()
        secrets = self._secrets()
        primary, fallback = settings.model.primary, settings.model.fallback
        return [
            {
                "id": "local",
                "provider": "local_mlx",
                "default": primary == "local",
                "fallback": fallback == "local",
                "enabled": True,
                "config": {"mode": settings.model.local.mode, "cwd": settings.model.local.cwd},
            },
            {
                "id": "deepseek",
                "provider": "deepseek",
                "default": primary == "deepseek",
                "fallback": fallback == "deepseek",
                "enabled": bool(secrets.get("DEEPSEEK_API_KEY")),
                "config": {
                    "model": settings.model.deepseek.model,
                    "base_url": settings.model.deepseek.base_url,
                },
            },
        ]

    # -- logs ---------------------------------------------------------
    def read_logs(self) -> list[str]:
        logs_dir = self._logs_dir()
        if not logs_dir.exists():
            return []
        return sorted(f.name for f in logs_dir.glob("*.log"))

    def read_log_tail(self, name: str, tail: int = 100) -> list[str]:
        if "/" in name or "\\" in name or ".." in name:
            raise ValueError(f"非法日志文件名：{name!r}")
        path = self._logs_dir() / name
        if not path.exists():
            raise FileNotFoundError(name)
        lines = path.read_text(encoding="utf-8").splitlines()
        return lines[-tail:]

    # -- scheduler ----------------------------------------------------
    def scheduler_status(self) -> list[dict]:
        from ..scheduler import status

        return status(project_dir=self.root)
