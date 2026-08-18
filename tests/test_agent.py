import tempfile
import unittest
from pathlib import Path

from agent_daily.agent import (
    ContextResolutionError,
    ExecutionContext,
    StepExecutionError,
    StepSpec,
    WorkflowAgent,
)
from agent_daily.output import OutputRegistry
from agent_daily.storage import ArtifactStore
from agent_daily.tools import ToolRegistry, ToolResult


class RecordingTool:
    name = "rec"
    description = ""
    parameters = {}

    def __init__(self, calls):
        self.calls = calls

    def run(self, args):
        self.calls.append(args)
        return ToolResult(success=True, data={"got": args})


class FailingTool:
    name = "fail"
    description = ""
    parameters = {}

    def run(self, args):
        raise RuntimeError("工具炸了")


class FakeModel:
    def __init__(self, result="model-out"):
        self.result = result
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return self.result


class FakePrompt:
    def __init__(self):
        self.calls = []

    def render(self, name, **vars_):
        self.calls.append((name, vars_))
        return f"rendered[{name}]{vars_}"


class FakeOutput:
    name = "fake_out"

    def __init__(self):
        self.calls = []

    def write(self, title, content, **kwargs):
        self.calls.append((title, content, kwargs))
        return "doc-1"


def _spec(id, type_, **extra):
    return StepSpec(id=id, type=type_, extra=extra)


def _agent(steps, model=None, tools=None, outputs=None, prompt=None, artifacts=None):
    model = model or FakeModel()
    tools = tools or ToolRegistry()
    outputs = outputs or OutputRegistry()
    prompt = prompt or FakePrompt()
    return WorkflowAgent(steps, model, tools, outputs, prompt, artifacts)


class TestContextResolve(unittest.TestCase):
    def setUp(self):
        self.ctx = ExecutionContext()
        self.ctx.set("collect", {"items": [{"name": "a", "stars": 10}, {"name": "b", "stars": 20}]})

    def test_simple_and_nested(self):
        self.assertEqual(self.ctx.resolve("${collect}"), self.ctx.data["collect"])
        self.assertEqual(self.ctx.resolve("${collect.items}"), self.ctx.data["collect"]["items"])
        self.assertEqual(self.ctx.resolve("${collect.items[0].name}"), "a")
        self.assertEqual(self.ctx.resolve("${collect.items[1].stars}"), 20)

    def test_interpolation_in_string(self):
        self.assertEqual(self.ctx.resolve("标题 ${collect.items[0].name}"), "标题 a")

    def test_recursive_dict_and_list(self):
        out = self.ctx.resolve({"x": "${collect.items[0].name}", "y": ["${collect.items[1].stars}"]})
        self.assertEqual(out, {"x": "a", "y": [20]})

    def test_missing_key_raises(self):
        with self.assertRaises(ContextResolutionError):
            self.ctx.resolve("${collect.nope}")

    def test_index_out_of_range_raises(self):
        with self.assertRaises(ContextResolutionError):
            self.ctx.resolve("${collect.items[9]}")


class TestWorkflow(unittest.TestCase):
    def test_sequential_order(self):
        calls = []
        tools = ToolRegistry()
        tools.register(RecordingTool(calls))
        steps = [
            _spec("s1", "tool", tool="rec", args={"n": 1}),
            _spec("s2", "tool", tool="rec", args={"n": 2}),
            _spec("s3", "tool", tool="rec", args={"n": 3}),
        ]
        agent = _agent(steps, tools=tools)
        ctx = agent.run()
        self.assertEqual(calls, [{"n": 1}, {"n": 2}, {"n": 3}])
        # 每个步骤结果写入上下文
        self.assertEqual(ctx.get("s1"), {"got": {"n": 1}})

    def test_tool_step_uses_resolved_args(self):
        calls = []
        tools = ToolRegistry()
        tools.register(RecordingTool(calls))
        steps = [
            _spec("seed", "tool", tool="rec", args={"v": 42}),
            _spec("use", "tool", tool="rec", args={"v": "${seed.got.v}"}),
        ]
        agent = _agent(steps, tools=tools)
        agent.run()
        self.assertEqual(calls[1], {"v": 42})

    def test_model_step(self):
        model = FakeModel("hello")
        prompt = FakePrompt()
        steps = [
            _spec("m", "model", prompt="summarize", variables={"repo_name": "x"}, max_tokens=10),
        ]
        agent = _agent(steps, model=model, prompt=prompt)
        ctx = agent.run()
        self.assertEqual(ctx.get("m"), "hello")
        self.assertEqual(prompt.calls[0][0], "summarize")
        self.assertEqual(prompt.calls[0][1], {"repo_name": "x"})
        self.assertEqual(model.calls[0][1]["max_tokens"], 10)
        # 组装了 user 消息
        self.assertEqual(model.calls[0][0][-1]["role"], "user")

    def test_output_step(self):
        out = FakeOutput()
        outputs = OutputRegistry()
        outputs.register(out)
        steps = [
            _spec("t", "tool", tool="rec", args={"x": 1}),
            _spec("o", "output", provider="fake_out", title="快报", content="${t.got.x}"),
        ]
        tools = ToolRegistry()
        tools.register(RecordingTool([]))
        agent = _agent(steps, tools=tools, outputs=outputs)
        ctx = agent.run()
        self.assertEqual(out.calls[0][0], "快报")
        self.assertEqual(out.calls[0][1], "1")
        self.assertEqual(ctx.get("o"), "doc-1")

    def test_artifact_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = ArtifactStore(Path(tmp) / "processed")
            steps = [
                _spec("save", "artifact", action="save", name="report", artifact_type="json",
                      content={"items": [1, 2]}, date="2026-08-16"),
                _spec("load", "artifact", action="load", name="report", artifact_type="json",
                      date="2026-08-16"),
            ]
            agent = _agent(steps, artifacts=artifacts)
            ctx = agent.run()
            self.assertEqual(ctx.get("load"), {"items": [1, 2]})
            self.assertTrue(artifacts.exists("report", "json", "2026-08-16"))

    def test_unknown_step_type_raises(self):
        agent = _agent([_spec("x", "mystery")])
        with self.assertRaises(StepExecutionError):
            agent.run()

    def test_step_failure_stops(self):
        calls = []
        tools = ToolRegistry()
        tools.register(RecordingTool(calls))
        tools.register(FailingTool())
        steps = [
            _spec("ok", "tool", tool="rec", args={}),
            _spec("bad", "tool", tool="fail", args={}),
            _spec("never", "tool", tool="rec", args={}),
        ]
        agent = _agent(steps, tools=tools)
        with self.assertRaises(StepExecutionError) as cm:
            agent.run()
        self.assertEqual(cm.exception.step_id, "bad")
        self.assertEqual(cm.exception.step_type, "tool")
        # 失败后不再执行后续步骤
        self.assertEqual(len(calls), 1)

    def test_execution_trace(self):
        calls = []
        tools = ToolRegistry()
        tools.register(RecordingTool(calls))
        tools.register(FailingTool())
        steps = [
            _spec("a", "tool", tool="rec", args={}),
            _spec("b", "tool", tool="fail", args={}),
        ]
        agent = _agent(steps, tools=tools)
        with self.assertRaises(StepExecutionError):
            agent.run()

        statuses = [(t["step"], t["status"]) for t in agent.trace]
        self.assertEqual(statuses, [
            ("a", "start"), ("a", "success"),
            ("b", "start"), ("b", "failure"),
        ])
        failure = [t for t in agent.trace if t["status"] == "failure"][0]
        self.assertIn("error", failure)


if __name__ == "__main__":
    unittest.main()
