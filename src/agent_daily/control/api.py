"""Control Plane FastAPI 路由（S1-A：只读后端）。

约束：本层只调用 repo（只读仓储），绝不执行 workflow / 调用 Tool / Model /
Output。secrets 只返回掩码。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from .. import __version__
from .repo import Repo


def create_app(repo: Repo | None = None) -> FastAPI:
    repo = repo or Repo()
    app = FastAPI(title="Agent Daily Control Plane", version=__version__)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/api/jobs")
    def jobs() -> list[dict]:
        return repo.read_jobs()

    @app.get("/api/runs")
    def runs(
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        job: str | None = None,
    ) -> dict:
        return repo.read_runs(limit=limit, offset=offset, job=job)

    @app.get("/api/artifacts")
    def artifacts(date: str | None = None) -> dict:
        return repo.read_artifacts(date=date)

    @app.get("/api/artifacts/{date}/{name}")
    def artifact(date: str, name: str) -> dict:
        try:
            return repo.read_artifact(date, name)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/config")
    def config() -> dict:
        return repo.read_config()

    @app.get("/api/logs")
    def logs() -> list[str]:
        return repo.read_logs()

    @app.get("/api/logs/{name}")
    def log_tail(name: str, tail: int = Query(100, ge=1, le=5000)) -> dict:
        try:
            return {"file": name, "lines": repo.read_log_tail(name, tail)}
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/scheduler/status")
    def scheduler_status() -> list[dict]:
        return repo.scheduler_status()

    @app.get("/api/models")
    def models() -> list[dict]:
        return repo.read_models()

    # 静态前端托管（仅当 frontend/dist 已构建时挂载；不改动任何 /api 端点）
    _mount_frontend(app, repo)

    return app


def _mount_frontend(app: FastAPI, repo: Repo) -> None:
    dist = Path(repo.root) / "frontend" / "dist"
    if dist.is_dir() and (dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")


app = create_app()
