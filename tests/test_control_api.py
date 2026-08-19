import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from agent_daily.control import Repo, create_app


def _make_project(tmp):
    root = Path(tmp)
    (root / "jobs").mkdir(parents=True)
    (root / "jobs" / "github_trending.yaml").write_text(
        "job: github_trending\nschedule: '09:00'\ndescription: 采集热榜\nenabled: true\n"
        "workflow:\n  steps:\n    - {id: a, type: tool, tool: x, args: {}}\noutputs: []\n",
        encoding="utf-8",
    )
    (root / "jobs" / "feishu_report.yaml").write_text(
        "job: feishu_report\nschedule: '10:00'\nenabled: false\n"
        "workflow:\n  steps:\n    - {id: a, type: tool, tool: x, args: {}}\noutputs: []\n",
        encoding="utf-8",
    )

    state = root / "data" / "state"
    state.mkdir(parents=True)
    (state / "job_runs.jsonl").write_text(
        json.dumps({"job": "github_trending", "status": "success", "artifacts": ["report"]}) + "\n"
        + json.dumps({"job": "feishu_report", "status": "failed", "error": "x"}) + "\n",
        encoding="utf-8",
    )

    processed = root / "data" / "processed" / "2026-08-16"
    (processed / ".meta").mkdir(parents=True)
    (processed / "trending_raw.json").write_text('{"items": [1, 2]}', encoding="utf-8")
    (processed / ".meta" / "trending_raw.json").write_text(
        json.dumps({"name": "trending_raw", "type": "json", "created_at": "2026-08-16T00:00:00+00:00"}),
        encoding="utf-8",
    )
    (processed / "report.md").write_text("# 快报\n正文", encoding="utf-8")

    logs = root / "data" / "logs"
    logs.mkdir(parents=True)
    (logs / "agent-daily.log").write_text("line1\nline2\nline3\n", encoding="utf-8")
    return root


class TestControlApi(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = _make_project(self._tmp.name)
        self.client = TestClient(create_app(Repo(self.root)))

    def tearDown(self):
        self._tmp.cleanup()

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_jobs(self):
        data = self.client.get("/api/jobs").json()
        ids = {j["id"]: j for j in data}
        self.assertIn("github_trending", ids)
        self.assertIn("feishu_report", ids)
        self.assertEqual(ids["github_trending"]["schedule"], "09:00")
        self.assertEqual(ids["github_trending"]["description"], "采集热榜")
        self.assertTrue(ids["github_trending"]["enabled"])
        self.assertFalse(ids["feishu_report"]["enabled"])
        self.assertEqual(ids["github_trending"]["last_status"], "success")

    def test_runs(self):
        data = self.client.get("/api/runs").json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["items"][0]["job"], "feishu_report")  # 反序最新在前
        filtered = self.client.get("/api/runs", params={"job": "github_trending"}).json()
        self.assertEqual(filtered["total"], 1)

    def test_artifacts_list(self):
        data = self.client.get("/api/artifacts", params={"date": "2026-08-16"}).json()
        self.assertIn("2026-08-16", data["dates"])
        names = {a["name"] for a in data["artifacts"]}
        self.assertIn("trending_raw", names)
        self.assertIn("report", names)

    def test_artifact_content(self):
        r = self.client.get("/api/artifacts/2026-08-16/trending_raw")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["content"], {"items": [1, 2]})

    def test_config_masks_secrets(self):
        data = self.client.get("/api/config").json()
        self.assertIn("config", data)
        self.assertIn("secrets", data)
        self.assertIsInstance(data["secrets"]["DEEPSEEK_API_KEY"], bool)

    def test_logs(self):
        self.assertEqual(self.client.get("/api/logs").json(), ["agent-daily.log"])
        r = self.client.get("/api/logs/agent-daily.log", params={"tail": 2})
        self.assertEqual(r.json()["lines"], ["line2", "line3"])

    def test_scheduler_status(self):
        r = self.client.get("/api/scheduler/status")
        self.assertEqual(r.status_code, 200)
        ids = {s["job"] for s in r.json()}
        self.assertIn("github_trending", ids)

    def test_models(self):
        data = self.client.get("/api/models").json()
        ids = {m["id"] for m in data}
        self.assertIn("local", ids)
        self.assertIn("deepseek", ids)
        local = next(m for m in data if m["id"] == "local")
        self.assertTrue(local["default"])


class TestRepoGuard(unittest.TestCase):
    def test_log_tail_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repo(Path(tmp))
            with self.assertRaises(ValueError):
                repo.read_log_tail("../secrets.env")


class TestRealData(unittest.TestCase):
    def test_real_jobs_readable(self):
        # 验收：默认 Repo 读取当前 v0.1.0 真实数据
        client = TestClient(create_app(Repo()))
        ids = {j["id"] for j in client.get("/api/jobs").json()}
        self.assertIn("github_trending", ids)
        self.assertIn("feishu_report", ids)


if __name__ == "__main__":
    unittest.main()
