"""命令行入口。

命令：
  doctor           环境自检
  run <job_id>     执行一个任务（加载→校验→WorkflowAgent→记录状态）
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-daily",
        description="个人 AI Agent 系统（macOS / Apple Silicon）",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="检查运行环境（Python/配置/mlxsvc/data）")
    sub.add_parser("config", help="打印合并后的配置（JSON）")

    run = sub.add_parser("run", help="执行一个任务")
    run.add_argument("job_id", help="任务 id（如 github_trending / feishu_report）")

    sched = sub.add_parser("scheduler", help="launchd 定时任务管理")
    sched_sub = sched.add_subparsers(dest="scheduler_action", required=True)
    sched_sub.add_parser("install", help="生成 plist 并 launchctl load")
    sched_sub.add_parser("uninstall", help="launchctl unload 并删除 plist")
    sched_sub.add_parser("status", help="查看任务注册状态")

    serve = sub.add_parser("serve", help="启动 Control Plane（FastAPI 只读后端）")
    serve.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    serve.add_argument("--port", type=int, default=8787, help="端口（默认 8787）")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        from .doctor import print_report, run_checks

        checks = run_checks()
        print_report(checks)
        return 0 if all(c.status != "FAIL" for c in checks) else 1

    if args.command == "config":
        return _cmd_config()

    if args.command == "run":
        return _cmd_run(args)

    if args.command == "scheduler":
        return _cmd_scheduler(args)

    if args.command == "serve":
        return _cmd_serve(args)

    parser.print_help()
    return 2


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .control.api import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


def _cmd_config() -> int:
    from dataclasses import asdict

    from .config.loader import load_config

    print(json.dumps(asdict(load_config()), ensure_ascii=False, indent=2))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    from .config.loader import PROJECT_ROOT, load_config, load_secrets
    from .jobs.registry import JobRegistry
    from .jobs.runner import JobRunner, build_agent_factory
    from .logging_util import setup_logging
    from .storage.artifacts import ArtifactStore
    from .storage.state import StateStore

    settings = load_config()
    secrets = load_secrets()
    setup_logging(settings.logging.level, PROJECT_ROOT / settings.logging.dir)

    registry = JobRegistry(PROJECT_ROOT / "jobs")
    artifacts = ArtifactStore(PROJECT_ROOT / settings.storage.processed_dir, settings.timezone)
    state = StateStore(PROJECT_ROOT / "data" / "state" / "job_runs.jsonl")
    factory = build_agent_factory(settings, secrets, PROJECT_ROOT)
    runner = JobRunner(registry, artifacts, state, factory, timezone=settings.timezone)

    result = runner.run(args.job_id)
    print(json.dumps(
        {"job": result.job_id, "status": result.status, "error": result.error},
        ensure_ascii=False, indent=2,
    ))
    return 0 if result.status == "success" else 1


def _cmd_scheduler(args: argparse.Namespace) -> int:
    from .scheduler import install_jobs, status, uninstall_jobs

    if args.scheduler_action == "install":
        for r in install_jobs():
            mark = "✓" if r["loaded"] else "✗"
            print(f"{mark} {r['job']:<20} {r['schedule']}")
        return 0

    if args.scheduler_action == "uninstall":
        for name in uninstall_jobs():
            print(f"✓ 已卸载 {name}")
        return 0

    if args.scheduler_action == "status":
        for r in status():
            print(f"{r['job']:<20} {r['schedule']:<8} {r['plist_status']}")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
