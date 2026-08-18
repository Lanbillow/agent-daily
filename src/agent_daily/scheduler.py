"""launchd 调度：从 jobs/*.yaml 自动生成 plist。

原则：
  - launchd 仅负责调度；业务逻辑保持在 ``agent-daily run <job_id>``。
  - scheduler 不复制任何 Job/Workflow/Agent 逻辑。
  - plist 由 jobs/*.yaml 自动生成，不允许人工维护。

时区：StartCalendarInterval 直接使用 YAML 的 schedule（跟随系统时区 Asia/Shanghai），
不做 UTC 转换。
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .config.loader import PROJECT_ROOT
from .jobs.registry import JobRegistry

LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
TEMPLATE_NAME = "com.agent-daily.job.plist.tpl"
DEFAULT_PATH = f"{Path.home()}/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def parse_schedule(schedule: str) -> tuple[int, int]:
    """解析 'HH:MM' → (hour, minute)；非法抛 ValueError。"""
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", schedule)
    if not m:
        raise ValueError(f"非法 schedule：{schedule!r}（应为 HH:MM）")
    hour, minute = int(m.group(1)), int(m.group(2))
    if hour > 23 or minute > 59:
        raise ValueError(f"非法 schedule：{schedule!r}（小时 0-23，分钟 0-59）")
    return hour, minute


def job_label(job_id: str) -> str:
    return f"com.agent-daily.{job_id.replace('_', '-')}"


def plist_filename(job_id: str) -> str:
    return f"{job_label(job_id)}.plist"


def discover_jobs(jobs_dir: str | Path) -> list[dict]:
    """扫描 jobs/*.yaml，返回按 schedule 排序的 [{job, schedule}]。"""
    specs = JobRegistry(jobs_dir).load_all()
    jobs = [{"job": s.job, "schedule": s.schedule} for s in specs.values()]
    jobs.sort(key=lambda j: parse_schedule(j["schedule"]))
    return jobs


def build_plist(
    job_id: str,
    schedule: str,
    project_dir: str | Path,
    uv_path: str,
    path_env: str,
    home: str,
) -> str:
    """渲染 plist XML（读模板 + 占位符替换）。"""
    hour, minute = parse_schedule(schedule)
    root = Path(project_dir)

    template_path = root / "scheduler" / "templates" / TEMPLATE_NAME
    if not template_path.exists():
        raise FileNotFoundError(f"模板缺失：{template_path}")
    tpl = template_path.read_text(encoding="utf-8")

    mapping = {
        "LABEL": job_label(job_id),
        "UV": uv_path,
        "JOB_ID": job_id,
        "PROJECT_DIR": str(root),
        "PATH": path_env,
        "HOME": home,
        "HOUR": hour,
        "MINUTE": minute,
        "STDOUT": f"{root}/data/logs/launchd/{job_id}.stdout.log",
        "STDERR": f"{root}/data/logs/launchd/{job_id}.stderr.log",
    }
    out = tpl
    for key, value in mapping.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out


def _uv_path() -> str:
    return shutil.which("uv") or str(Path.home() / ".local" / "bin" / "uv")


def _run(cmd: list[str]) -> bool:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0


def install_jobs(
    project_dir: str | Path | None = None,
    launch_agents_dir: str | Path | None = None,
) -> list[dict]:
    """生成 plist → 复制到 LaunchAgents → launchctl load。"""
    root = Path(project_dir) if project_dir else PROJECT_ROOT
    lad = Path(launch_agents_dir) if launch_agents_dir else LAUNCH_AGENTS_DIR
    lad.mkdir(parents=True, exist_ok=True)

    uv = _uv_path()
    results = []
    for job in discover_jobs(root / "jobs"):
        plist_xml = build_plist(
            job["job"], job["schedule"], root, uv, DEFAULT_PATH, str(Path.home())
        )
        plist_path = lad / plist_filename(job["job"])
        plist_path.write_text(plist_xml, encoding="utf-8")
        loaded = _run(["launchctl", "load", str(plist_path)])
        results.append({
            "job": job["job"],
            "schedule": job["schedule"],
            "plist": str(plist_path),
            "loaded": loaded,
        })
    return results


def uninstall_jobs(
    project_dir: str | Path | None = None,
    launch_agents_dir: str | Path | None = None,
) -> list[str]:
    """launchctl unload + 删除 plist。"""
    root = Path(project_dir) if project_dir else PROJECT_ROOT
    lad = Path(launch_agents_dir) if launch_agents_dir else LAUNCH_AGENTS_DIR
    removed = []
    for job in discover_jobs(root / "jobs"):
        plist_path = lad / plist_filename(job["job"])
        if plist_path.exists():
            _run(["launchctl", "unload", str(plist_path)])
            plist_path.unlink(missing_ok=True)
            removed.append(job["job"])
    return removed


def status(
    project_dir: str | Path | None = None,
    launch_agents_dir: str | Path | None = None,
) -> list[dict]:
    """返回每个任务的 {job, schedule, plist_status}。"""
    root = Path(project_dir) if project_dir else PROJECT_ROOT
    lad = Path(launch_agents_dir) if launch_agents_dir else LAUNCH_AGENTS_DIR
    loaded_labels = _loaded_labels()

    results = []
    for job in discover_jobs(root / "jobs"):
        label = job_label(job["job"])
        plist_exists = (lad / plist_filename(job["job"])).exists()
        if label in loaded_labels:
            plist_status = "loaded"
        elif plist_exists:
            plist_status = "not-loaded"
        else:
            plist_status = "missing"
        results.append({
            "job": job["job"],
            "schedule": job["schedule"],
            "plist_status": plist_status,
        })
    return results


def _loaded_labels() -> set[str]:
    proc = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    if proc.returncode != 0:
        return set()
    return set(proc.stdout.split())
