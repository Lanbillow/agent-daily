"""Workflow Agent —— 第一阶段 Agent 核心（确定性编排器）。

不是自主 ReAct Agent。职责：
  读取 workflow.steps → 顺序执行 → 保存结果到 ExecutionContext → 返回上下文。

禁止：自主规划 / 修改 workflow / 自动创建步骤 / 引入循环。

失败策略：任何 step 失败立即停止，记录 trace（step 开始/成功/失败 + 错误），
并向上抛 StepExecutionError（禁止吞异常）。
"""

from __future__ import annotations

from typing import Any

from .context import ExecutionContext
from .memory import Memory, NullMemory
from .steps import StepExecutionError, StepExecutor, StepSpec


class WorkflowAgent:
    def __init__(
        self,
        steps: list[StepSpec],
        model: Any,
        tools: Any,
        outputs: Any,
        prompt: Any,
        artifacts: Any,
        memory: Memory | None = None,
    ) -> None:
        self.steps = steps
        self.memory = memory or NullMemory()
        self.trace: list[dict[str, Any]] = []
        self._executor = StepExecutor(model, tools, outputs, prompt, artifacts)

    def run(self, task_input: dict[str, Any] | None = None) -> ExecutionContext:
        """顺序执行 steps，返回含各步骤结果的上下文。"""
        ctx = ExecutionContext()
        if task_input:
            ctx.data.update(task_input)

        self.trace = []
        for step in self.steps:
            self.trace.append({"step": step.id, "type": step.type, "status": "start"})
            try:
                result = self._executor.run(step, ctx)
                ctx.set(step.id, result)
                self.trace.append({"step": step.id, "type": step.type, "status": "success"})
            except StepExecutionError as exc:
                self.trace.append(
                    {"step": step.id, "type": step.type, "status": "failure", "error": str(exc)}
                )
                raise

        return ctx
