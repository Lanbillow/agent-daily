import json
import tempfile
import unittest
from pathlib import Path

from agent_daily.jobs import JobConfigError, JobRegistry, JobRunner
from agent_daily.storage import ArtifactStore, StateStore

JOB_BODY = """
job: github_trending
schedule: "09:00"
workflow:
  steps:
    - id: collect
      type: tool
      tool: github_trending
      args:
        since: daily
    - id: save
      type: artifact
      action: save
      name: report
      artifact_type: markdown
      date: ${date}
      content: ${collect}
outputs:
  - {name: report, type: markdown}
"""


class FakeAgent:
    def __init__(self, artifacts, fail=False, write_outputs=True):
        self.artifacts = artifacts
        self.fail = fail
        self.write_outputs = write_outputs
        self.spec = None  # 由 factory 注入
        self.called = False
        self.task_input = None

    def run(self, task_input=None):
        self.called = True
        self.task_input = task_input
        if self.fail:
            raise RuntimeError("agent 执行失败")
        if self.write_outputs:
            for o in self.spec.outputs:
                self.artifacts.save(o.name, o.type, "x", date=task_input["date"])
        return None


class JobsTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.jobs_dir = self.root / "jobs"
        self.jobs_dir.mkdir()
        self.registry = JobRegistry(self.jobs_dir)
        self.artifacts = ArtifactStore(self.root / "processed")
        self.state = StateStore(self.root / "state" / "job_runs.jsonl")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_job(self, name, body):
        (self.jobs_dir / f"{name}.yaml").write_text(body, encoding="utf-8")

    def _runner(self, agent):
        def factory(spec):
            agent.spec = spec
            return agent

        return JobRunner(self.registry, self.artifacts, self.state, factory)


class TestRegistry(JobsTestCase):
    def test_load_job_yaml(self):
        self._write_job("job1", JOB_BODY)
        spec = self.registry.get("github_trending")
        self.assertEqual(spec.job, "github_trending")
        self.assertEqual(spec.schedule, "09:00")
        self.assertEqual(len(spec.workflow), 2)
        self.assertEqual(spec.workflow[0].type, "tool")
        self.assertEqual(spec.outputs[0].name, "report")
        self.assertEqual(spec.outputs[0].type, "markdown")

    def test_invalid_yaml(self):
        self._write_job("job1", "::not yaml::")
        with self.assertRaises(JobConfigError):
            self.registry.load_all()

    def test_missing_job_field(self):
        self._write_job("job1", "schedule: '09:00'\nworkflow:\n  steps: []\n")
        with self.assertRaises(JobConfigError):
            self.registry.load_all()

    def test_invalid_step_type(self):
        self._write_job("job1", "job: x\nworkflow:\n  steps:\n    - {id: a, type: magic}\n")
        with self.assertRaises(JobConfigError):
            self.registry.load_all()

    def test_unknown_job_raises(self):
        with self.assertRaises(JobConfigError):
            self.registry.get("nope")


class TestRunner(JobsTestCase):
    def test_inputs_missing_detected(self):
        self._write_job(
            "job1",
            "job: feishu_report\nworkflow:\n  steps:\n    - {id: a, type: tool, tool: rec, args: {}}\n"
            "inputs:\n  - {name: report, type: markdown}\n",
        )
        result = self._runner(FakeAgent(self.artifacts)).run("feishu_report")
        self.assertEqual(result.status, "failed")
        self.assertIn("输入工件缺失", result.error)

    def test_outputs_contract_validation(self):
        self._write_job("job1", JOB_BODY)
        agent = FakeAgent(self.artifacts, write_outputs=False)
        result = self._runner(agent).run("github_trending")
        self.assertEqual(result.status, "failed")
        self.assertIn("输出工件缺失", result.error)

    def test_workflow_agent_invoked(self):
        self._write_job("job1", JOB_BODY)
        agent = FakeAgent(self.artifacts)
        result = self._runner(agent).run("github_trending")
        self.assertTrue(agent.called)
        self.assertIn("date", agent.task_input)
        self.assertEqual(result.status, "success")

    def test_state_success_record(self):
        self._write_job("job1", JOB_BODY)
        self._runner(FakeAgent(self.artifacts)).run("github_trending")
        hist = self.state.history()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["job"], "github_trending")
        self.assertEqual(hist[0]["status"], "success")
        self.assertEqual(hist[0]["artifacts"], ["report"])

    def test_state_failure_record(self):
        self._write_job("job1", JOB_BODY)
        agent = FakeAgent(self.artifacts, fail=True)
        result = self._runner(agent).run("github_trending")
        self.assertEqual(result.status, "failed")
        hist = self.state.history()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["status"], "failed")
        self.assertIn("error", hist[0])
        self.assertIn("agent 执行失败", hist[0]["error"])


class TestRealDefinitions(unittest.TestCase):
    def test_real_jobs_and_prompts_load(self):
        from agent_daily.prompt import PromptManager

        root = Path(__file__).resolve().parents[1]
        registry = JobRegistry(root / "jobs")
        specs = registry.load_all()
        self.assertEqual(set(specs), {"github_trending", "feishu_report"})

        pm = PromptManager(root / "prompts")
        self.assertEqual(pm.load("summarize_repo").variables,
                         ["repo_name", "description", "language", "stars"])
        self.assertEqual(pm.load("compose_report").variables, ["date", "summaries"])


class TestEndToEnd(unittest.TestCase):
    """端到端闭环：真实 YAML + 真实 Prompt + 真实 WorkflowAgent + 真实 ArtifactStore，
    仅数据源与模型用 fake（验证 wiring 与工件产出）。"""

    def test_pipeline_produces_three_artifacts(self):
        from agent_daily.agent import WorkflowAgent
        from agent_daily.output import OutputRegistry, LocalFileProvider
        from agent_daily.prompt import PromptManager
        from agent_daily.tools import ToolRegistry
        from agent_daily.tools.github_trending import GithubTrendingTool
        from agent_daily.tools.report_composer import ReportComposerTool
        from agent_daily.tools.report_composer import SummaryNormalizerTool

        root = Path(__file__).resolve().parents[1]
        spec = JobRegistry(root / "jobs").get("github_trending")

        class FakeSource:
            name = "mirror"
            format = "json"
            base_url = "https://m.example.com"

            def fetch(self, since="daily"):
                return json.dumps([
                    {"name": "owner/a", "description": "项目A", "language": "Python",
                     "stars": 100, "url": "https://x/a"},
                    {"name": "owner/b", "description": "项目B", "language": "Go",
                     "stars": 200, "url": "https://x/b"},
                ])

        class FakeAdapter:
            def get_source(self):
                return FakeSource()

        class FakeModel:
            def __init__(self):
                self.calls = 0

            def chat(self, messages, **kwargs):
                self.calls += 1
                return "中文摘要内容"

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            model = FakeModel()
            prompt = PromptManager(root / "prompts")
            tools = ToolRegistry()
            tools.register(GithubTrendingTool(FakeAdapter()))
            tools.register(ReportComposerTool())
            tools.register(SummaryNormalizerTool())
            outputs = OutputRegistry()
            outputs.register(LocalFileProvider(base / "output"))
            artifacts = ArtifactStore(base / "processed")

            agent = WorkflowAgent(spec.workflow, model, tools, outputs, prompt, artifacts)
            ctx = agent.run(task_input={"date": "2026-08-16"})

            # 3 个工件产出
            self.assertTrue(artifacts.exists("trending_raw", "json", "2026-08-16"))
            self.assertTrue(artifacts.exists("summaries", "json", "2026-08-16"))
            self.assertTrue(artifacts.exists("report", "markdown", "2026-08-16"))

            summaries = artifacts.load("summaries", "json", "2026-08-16")
            self.assertEqual(len(summaries), 2)
            self.assertEqual(summaries[0]["name"], "owner/a")
            self.assertEqual(summaries[0]["summary"], "中文摘要内容")

            report = artifacts.load("report", "markdown", "2026-08-16")
            self.assertIn("中文摘要内容", report)
            # 仅逐条摘要调用模型；报告由确定性工具完整组装
            self.assertEqual(model.calls, 2)


if __name__ == "__main__":
    unittest.main()
