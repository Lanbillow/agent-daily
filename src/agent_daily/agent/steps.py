"""Workflow 步骤定义与执行器。

四类步骤（确定性，无自主规划）：
  tool     调用 ToolRegistry 中的工具
  model    用 PromptManager 渲染模板 + ModelManager 调用模型
  artifact 调用 ArtifactStore（load / save），跨任务唯一数据来源
  output   调用 OutputProvider（禁止直接调用具体实现）

失败策略：任何失败抛 StepExecutionError（携带 step_id / step_type / error），
由 WorkflowAgent 记录 trace 并立即中断。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..storage.artifacts import ArtifactStore
from ..tools.base import ToolRegistry, ToolResult
from .context import ExecutionContext


@dataclass
class StepSpec:
    """一条 workflow 步骤（来自 job YAML 的 workflow.steps）。"""

    id: str
    type: str  # tool | model | artifact | output
    extra: dict[str, Any] = field(default_factory=dict)


class StepExecutionError(Exception):
    """步骤执行失败。"""

    def __init__(self, step_id: str, step_type: str, message: str) -> None:
        self.step_id = step_id
        self.step_type = step_type
        super().__init__(f"step 失败 [{step_id}] ({step_type}): {message}")


class StepExecutor:
    """执行单条步骤，持有所有依赖（model/tools/outputs/prompt/artifacts）。"""

    def __init__(
        self,
        model: Any,
        tools: ToolRegistry,
        outputs: Any,
        prompt: Any,
        artifacts: ArtifactStore,
    ) -> None:
        self.model = model
        self.tools = tools
        self.outputs = outputs
        self.prompt = prompt
        self.artifacts = artifacts

    def run(self, step: StepSpec, ctx: ExecutionContext) -> Any:
        handler = {
            "tool": self._run_tool,
            "model": self._run_model,
            "artifact": self._run_artifact,
            "output": self._run_output,
        }.get(step.type)
        if handler is None:
            raise StepExecutionError(step.id, step.type, f"未知步骤类型 {step.type!r}")

        try:
            return handler(step, ctx)
        except StepExecutionError:
            raise
        except Exception as exc:
            raise StepExecutionError(step.id, step.type, str(exc)) from exc

    # -- tool ----------------------------------------------------------
    def _run_tool(self, step: StepSpec, ctx: ExecutionContext) -> Any:
        tool_name = step.extra.get("tool")
        if not tool_name:
            raise StepExecutionError(step.id, step.type, "缺少 tool 字段")
        try:
            tool = self.tools.get(str(tool_name))
        except KeyError as exc:
            raise StepExecutionError(step.id, step.type, f"未注册工具：{tool_name}") from exc

        args = ctx.resolve(step.extra.get("args") or {})
        result = tool.run(args)
        if isinstance(result, ToolResult):
            if not result.success:
                raise StepExecutionError(step.id, step.type, result.error or "工具执行失败")
            return result.data
        return result

    # -- model ---------------------------------------------------------
    def _run_model(self, step: StepSpec, ctx: ExecutionContext) -> Any:
        prompt_name = step.extra.get("prompt")
        if not prompt_name:
            raise StepExecutionError(step.id, step.type, "缺少 prompt 字段")

        if step.extra.get("batch") or step.extra.get("input") is not None:
            return self._run_model_batch(step, ctx, str(prompt_name))

        variables = ctx.resolve(step.extra.get("variables") or {})
        rendered = self.prompt.render(str(prompt_name), **variables)
        messages = self._build_messages(step, ctx, rendered)
        return self.model.chat(messages, **self._gen_params(step))

    def _run_model_batch(
        self, step: StepSpec, ctx: ExecutionContext, prompt_name: str
    ) -> Any:
        items = ctx.resolve(step.extra["input"])
        if not isinstance(items, list):
            raise StepExecutionError(step.id, step.type, "batch 模式 input 必须是列表")

        map_spec = step.extra.get("map") or {}
        result_key = step.extra.get("result_key", "output")
        results: list[Any] = []
        for item in items:
            ctx.set("item", item)
            try:
                variables = ctx.resolve(map_spec)
                rendered = self.prompt.render(prompt_name, **variables)
                messages = self._build_messages(step, ctx, rendered)
                output = self.model.chat(messages, **self._gen_params(step))
                if isinstance(item, dict):
                    entry = dict(item)
                    entry[result_key] = output
                    results.append(entry)
                else:
                    results.append(output)
            finally:
                ctx.data.pop("item", None)
        return results

    def _build_messages(
        self, step: StepSpec, ctx: ExecutionContext, rendered: str
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        system = step.extra.get("system")
        if system:
            messages.append({"role": "system", "content": str(ctx.resolve(system))})
        messages.append({"role": "user", "content": rendered})
        return messages

    def _gen_params(self, step: StepSpec) -> dict[str, Any]:
        gen: dict[str, Any] = {}
        if step.extra.get("max_tokens") is not None:
            gen["max_tokens"] = step.extra["max_tokens"]
        if step.extra.get("temperature") is not None:
            gen["temperature"] = step.extra["temperature"]
        return gen

    # -- artifact ------------------------------------------------------
    def _run_artifact(self, step: StepSpec, ctx: ExecutionContext) -> Any:
        action = step.extra.get("action")
        name = step.extra.get("name")
        artifact_type = step.extra.get("artifact_type") or step.extra.get("format")
        date = ctx.resolve(step.extra.get("date"))

        if not name or not artifact_type:
            raise StepExecutionError(step.id, step.type, "缺少 name/artifact_type 字段")

        if action == "save":
            content = ctx.resolve(step.extra.get("content"))
            return self.artifacts.save(str(name), str(artifact_type), content, date=date)
        if action == "load":
            return self.artifacts.load(str(name), str(artifact_type), date=date)
        raise StepExecutionError(step.id, step.type, f"未知 artifact action：{action!r}")

    # -- output --------------------------------------------------------
    def _run_output(self, step: StepSpec, ctx: ExecutionContext) -> Any:
        provider_name = step.extra.get("provider")
        if not provider_name:
            raise StepExecutionError(step.id, step.type, "缺少 provider 字段")
        provider = self._get_output_provider(step)

        title = ctx.resolve(step.extra.get("title", ""))
        content = ctx.resolve(step.extra.get("content", ""))
        kwargs: dict[str, Any] = {}
        if step.extra.get("key") is not None:
            kwargs["key"] = ctx.resolve(step.extra["key"])
        return provider.write(str(title), str(content), **kwargs)

    def _get_output_provider(self, step: StepSpec) -> Any:
        provider_name = str(step.extra["provider"])
        try:
            return self.outputs.get(provider_name)
        except KeyError:
            fallback_name = step.extra.get("fallback")
            if fallback_name:
                try:
                    return self.outputs.get(str(fallback_name))
                except KeyError as exc:
                    raise StepExecutionError(
                        step.id, step.type,
                        f"未注册输出提供者：{provider_name} 及 fallback {fallback_name}",
                    ) from exc
            raise StepExecutionError(
                step.id, step.type, f"未注册输出提供者：{provider_name}"
            )
