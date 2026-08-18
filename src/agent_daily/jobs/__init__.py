"""任务模块：注册表 + 执行器 + 依赖装配。"""

from .registry import JobConfigError, JobRegistry, JobSpec
from .runner import JobError, JobResult, JobRunner, build_agent_factory

__all__ = [
    "JobSpec",
    "JobRegistry",
    "JobConfigError",
    "JobRunner",
    "JobResult",
    "JobError",
    "build_agent_factory",
]
