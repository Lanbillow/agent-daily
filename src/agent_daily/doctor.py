"""环境自检（doctor）。

检查项（均可独立运行，便于单测）：
  1. Python 版本  2. 架构 (Apple Silicon)  3. 配置文件存在
  4. 配置模板存在  5. 密钥文件存在(可选)   6. mlxsvc 路径存在
  7. data 目录可写
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from pathlib import Path

from .config.loader import (
    CONFIG_EXAMPLE_FILE,
    CONFIG_FILE,
    SECRETS_FILE,
    load_config,
    mlxsvc_dir,
)

_STATUS_OK = "OK"
_STATUS_WARN = "WARN"
_STATUS_FAIL = "FAIL"


@dataclass
class CheckResult:
    name: str
    status: str  # OK | WARN | FAIL
    detail: str


def check_python_version() -> CheckResult:
    v = sys.version_info
    ok = v >= (3, 11)
    return CheckResult(
        "Python 版本",
        _STATUS_OK if ok else _STATUS_FAIL,
        f"{platform.python_version()} (需 >= 3.11)",
    )


def check_architecture() -> CheckResult:
    machine = platform.machine()
    system = platform.system()
    if system != "Darwin" or machine != "arm64":
        return CheckResult(
            "Apple Silicon 架构",
            _STATUS_WARN,
            f"{system}/{machine} (建议 arm64/macOS)",
        )
    return CheckResult("Apple Silicon 架构", _STATUS_OK, f"{system}/{machine}")


def check_config_file(path: Path | None = None) -> CheckResult:
    p = path or CONFIG_FILE
    if p.exists():
        return CheckResult("配置文件 config.yaml", _STATUS_OK, str(p))
    return CheckResult(
        "配置文件 config.yaml",
        _STATUS_WARN,
        f"缺失：{p}（可复制 config.yaml.example）",
    )


def check_config_example(path: Path | None = None) -> CheckResult:
    p = path or CONFIG_EXAMPLE_FILE
    if p.exists():
        return CheckResult("配置模板 config.yaml.example", _STATUS_OK, str(p))
    return CheckResult("配置模板 config.yaml.example", _STATUS_FAIL, f"缺失：{p}")


def check_secrets_file(path: Path | None = None) -> CheckResult:
    p = path or SECRETS_FILE
    if p.exists():
        return CheckResult("密钥文件 secrets.env", _STATUS_OK, str(p))
    return CheckResult(
        "密钥文件 secrets.env",
        _STATUS_WARN,
        f"缺失：{p}（本地/离线运行可不配，远程模型与飞书需配）",
    )


def check_mlxsvc(path: Path | None = None) -> CheckResult:
    p = path if path is not None else mlxsvc_dir(load_config())
    if p.exists():
        return CheckResult("mlxsvc 路径", _STATUS_OK, str(p))
    return CheckResult("mlxsvc 路径", _STATUS_FAIL, f"缺失：{p}")


def check_data_writable(data_dir: Path) -> CheckResult:
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".doctor_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return CheckResult("data 目录可写", _STATUS_OK, str(data_dir))
    except OSError as exc:
        return CheckResult("data 目录可写", _STATUS_FAIL, f"{data_dir}: {exc}")


def check_launchd_available() -> CheckResult:
    lad = Path.home() / "Library" / "LaunchAgents"
    if lad.exists():
        return CheckResult("launchd (LaunchAgents)", _STATUS_OK, str(lad))
    return CheckResult(
        "launchd (LaunchAgents)", _STATUS_WARN, f"不存在：{lad}（install-jobs.sh 会创建）"
    )


def check_uv_available() -> CheckResult:
    import shutil

    uv = shutil.which("uv")
    if uv:
        return CheckResult("agent-daily CLI 可执行 (uv)", _STATUS_OK, uv)
    return CheckResult(
        "agent-daily CLI 可执行 (uv)", _STATUS_FAIL, "未找到 uv（定时任务无法启动）"
    )


def check_plists_generated() -> CheckResult:
    from .config.loader import PROJECT_ROOT
    from .scheduler import discover_jobs, plist_filename

    lad = Path.home() / "Library" / "LaunchAgents"
    try:
        jobs = discover_jobs(PROJECT_ROOT / "jobs")
    except Exception as exc:
        return CheckResult("scheduler plist 已生成", _STATUS_WARN, f"无法读取 jobs：{exc}")

    missing = [j["job"] for j in jobs if not (lad / plist_filename(j["job"])).exists()]
    if missing:
        return CheckResult(
            "scheduler plist 已生成", _STATUS_WARN,
            f"未生成：{missing}（运行 bash scheduler/install-jobs.sh）",
        )
    return CheckResult("scheduler plist 已生成", _STATUS_OK, f"{len(jobs)} 个任务")


def check_launchd_log_writable() -> CheckResult:
    from .config.loader import PROJECT_ROOT

    p = PROJECT_ROOT / "data" / "logs" / "launchd"
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".doctor_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return CheckResult("launchd 日志目录可写", _STATUS_OK, str(p))
    except OSError as exc:
        return CheckResult("launchd 日志目录可写", _STATUS_FAIL, f"{p}: {exc}")


def run_checks(data_dir: Path | None = None) -> list[CheckResult]:
    """执行全部检查并返回结果列表。"""
    from .config.loader import PROJECT_ROOT

    settings = load_config()
    data = data_dir or (PROJECT_ROOT / settings.storage.data_dir)

    return [
        check_python_version(),
        check_architecture(),
        check_config_file(),
        check_config_example(),
        check_secrets_file(),
        check_mlxsvc(mlxsvc_dir(settings)),
        check_data_writable(data),
        check_launchd_available(),
        check_uv_available(),
        check_plists_generated(),
        check_launchd_log_writable(),
    ]


def print_report(checks: list[CheckResult]) -> None:
    """打印对齐的自检报告。"""
    width = max(len(c.name) for c in checks) + 2
    for c in checks:
        print(f"[{c.status:<4}] {c.name:<{width}} {c.detail}")
    failed = sum(1 for c in checks if c.status == _STATUS_FAIL)
    print("-" * 60)
    if failed == 0:
        print("doctor 结果：通过")
    else:
        print(f"doctor 结果：{failed} 项失败")
