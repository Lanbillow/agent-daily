"""任务执行器。

Job 层职责：加载任务定义 → 校验输入输出契约 → 启动 WorkflowAgent。
JobRunner 不直接调用 Tool / Model / Output，一切执行经 WorkflowAgent。

流程：
  1. 加载 JobSpec
  2. 校验 inputs artifact 存在
  3. 装配依赖（ModelManager/PromptManager/ToolRegistry/OutputRegistry/ArtifactStore）
  4. 创建 WorkflowAgent
  5. 执行 workflow
  6. 校验 outputs
  7. 记录 StateStore（成功 / 失败均记录，失败含 error）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from ..config.schema import Settings
from .registry import JobRegistry, JobSpec


class JobError(Exception):
    """任务执行 / 契约校验失败。"""


@dataclass
class JobResult:
    job_id: str
    status: str  # success | failed
    outputs: dict[str, str] = field(default_factory=dict)
    error: str | None = None


def _now_iso() -> str:
    return datetime.now(ZoneInfo("UTC")).isoformat()


def _today(timezone: str) -> str:
    return datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d")


class JobRunner:
    def __init__(
        self,
        registry: JobRegistry,
        artifacts: Any,
        state: Any,
        agent_factory: Callable[[JobSpec], Any],
        timezone: str = "Asia/Shanghai",
    ) -> None:
        self.registry = registry
        self.artifacts = artifacts
        self.state = state
        self.agent_factory = agent_factory
        self.timezone = timezone

    def run(self, job_id: str) -> JobResult:
        spec = self.registry.get(job_id)
        start = _now_iso()
        date = _today(self.timezone)
        try:
            self._validate_inputs(spec, date)
            agent = self.agent_factory(spec)
            agent.run(task_input={"date": date})
            outputs = self._validate_outputs(spec, date)
            self.state.log_run(
                job_id, "success", start_time=start, end_time=_now_iso(),
                artifacts=sorted(outputs.keys()),
            )
            return JobResult(job_id, "success", outputs)
        except Exception as exc:
            self.state.log_run(
                job_id, "failed", start_time=start, end_time=_now_iso(),
                artifacts=[], error=str(exc),
            )
            return JobResult(job_id, "failed", error=str(exc))

    def _validate_inputs(self, spec: JobSpec, date: str) -> None:
        missing = [
            i.name for i in spec.inputs
            if not self.artifacts.exists(i.name, i.type, date=date)
        ]
        if missing:
            raise JobError(f"输入工件缺失：{missing}")

    def _validate_outputs(self, spec: JobSpec, date: str) -> dict[str, str]:
        missing = [
            o.name for o in spec.outputs
            if not self.artifacts.exists(o.name, o.type, date=date)
        ]
        if missing:
            raise JobError(f"输出工件缺失：{missing}")
        return {
            o.name: str(self.artifacts.resolve_path(o.name, o.type, date=date))
            for o in spec.outputs
        }


def build_agent_factory(
    settings: Settings,
    secrets: dict[str, str],
    project_root: str | Path | None = None,
) -> Callable[[JobSpec], Any]:
    """装配依赖并返回 agent_factory(spec) -> WorkflowAgent。"""
    from ..agent.core import WorkflowAgent
    from ..config.loader import PROJECT_ROOT
    from ..model.manager import create_model_manager
    from ..output.base import OutputRegistry
    from ..output.feishu import FeishuProvider
    from ..output.feishu_cli import FeishuCLIProvider
    from ..output.local_file import LocalFileProvider
    from ..prompt.manager import PromptManager
    from ..storage.artifacts import ArtifactStore
    from ..tools.base import ToolRegistry
    from ..tools.github_trending import GithubTrendingTool, SourceAdapter

    root = Path(project_root) if project_root else PROJECT_ROOT

    model = create_model_manager(settings, secrets, root)
    prompt = PromptManager(root / "prompts")

    tools = ToolRegistry()
    tools.register(GithubTrendingTool(SourceAdapter(settings.github)))

    outputs = OutputRegistry()
    outputs.register(LocalFileProvider(root / settings.output.local_file.dir))

    app_id = secrets.get("FEISHU_APP_ID", "")
    app_secret = secrets.get("FEISHU_APP_SECRET", "")
    if settings.output.feishu.enabled and app_id and app_secret:
        outputs.register(FeishuProvider(
            app_id,
            app_secret,
            folder_token=settings.output.feishu.folder_token,
            record_path=str(root / "data" / "output" / "feishu_records.json"),
        ))

    outputs.register(FeishuCLIProvider(
        command=settings.output.feishu_cli.command,
        timeout_seconds=settings.output.feishu_cli.timeout_seconds,
    ))
    outputs.set_default(settings.output.default)

    artifacts = ArtifactStore(root / settings.storage.processed_dir, settings.timezone)

    def factory(spec: JobSpec) -> WorkflowAgent:
        return WorkflowAgent(spec.workflow, model, tools, outputs, prompt, artifacts)

    return factory
