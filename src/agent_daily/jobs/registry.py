"""任务注册表：加载 jobs/*.yaml → JobSpec。

任务定义是数据（YAML），非代码。未来 UI 增删任务即编辑这些文件。

错误：YAML 非法 / 缺字段 / 非法 step 类型，一律抛 JobConfigError（明确报错）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..agent.steps import StepSpec
from ..storage.artifacts import ArtifactSpec

STEP_TYPES = ("tool", "model", "artifact", "output")


class JobConfigError(Exception):
    """任务定义非法。"""


@dataclass
class JobSpec:
    """一条任务定义。"""

    job: str
    schedule: str = ""
    model: str | None = None
    workflow: list[StepSpec] = field(default_factory=list)
    inputs: list[ArtifactSpec] = field(default_factory=list)
    outputs: list[ArtifactSpec] = field(default_factory=list)


class JobRegistry:
    def __init__(self, jobs_dir: str | Path) -> None:
        self.jobs_dir = Path(jobs_dir)

    def load_all(self) -> dict[str, JobSpec]:
        specs: dict[str, JobSpec] = {}
        for path in sorted(self.jobs_dir.glob("*.yaml")):
            spec = self._load_file(path)
            specs[spec.job] = spec
        return specs

    def get(self, job_id: str) -> JobSpec:
        specs = self.load_all()
        if job_id not in specs:
            raise JobConfigError(f"未找到任务：{job_id!r}（可用：{sorted(specs)}）")
        return specs[job_id]

    def _load_file(self, path: Path) -> JobSpec:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise JobConfigError(f"Job YAML 非法：{path}（{exc}）") from exc
        if not isinstance(data, dict):
            raise JobConfigError(f"Job 定义必须是映射：{path}")

        job = data.get("job")
        if not job:
            raise JobConfigError(f"缺少 job 字段：{path}")

        workflow = data.get("workflow") or {}
        steps = [self._parse_step(s, path) for s in workflow.get("steps", [])]
        if not steps:
            raise JobConfigError(f"workflow.steps 为空：{path}")

        inputs = [self._parse_artifact(a, path, "inputs") for a in (data.get("inputs") or [])]
        outputs = [self._parse_artifact(a, path, "outputs") for a in (data.get("outputs") or [])]

        return JobSpec(
            job=str(job),
            schedule=str(data.get("schedule", "")),
            model=data.get("model"),
            workflow=steps,
            inputs=inputs,
            outputs=outputs,
        )

    def _parse_step(self, step: Any, path: Path) -> StepSpec:
        if not isinstance(step, dict):
            raise JobConfigError(f"step 必须是映射：{path}")
        step_id = step.get("id")
        step_type = step.get("type")
        if not step_id or not step_type:
            raise JobConfigError(f"step 缺少 id/type：{path}")
        if step_type not in STEP_TYPES:
            raise JobConfigError(f"非法 step 类型 {step_type!r}：{path}")
        extra = {k: v for k, v in step.items() if k not in ("id", "type")}
        return StepSpec(id=str(step_id), type=str(step_type), extra=extra)

    def _parse_artifact(self, a: Any, path: Path, where: str) -> ArtifactSpec:
        if not isinstance(a, dict):
            raise JobConfigError(f"{where} 条目必须是映射：{path}")
        name = a.get("name")
        type_ = a.get("type")
        if not name or not type_:
            raise JobConfigError(f"{where} 条目缺少 name/type：{path}")
        return ArtifactSpec(name=str(name), type=str(type_), path=str(a.get("path", "")))
