import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from agent_daily.storage import ArtifactStore, StateStore


class TestArtifactStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "processed"
        self.store = ArtifactStore(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_json_roundtrip(self):
        data = {"items": [1, 2, 3], "title": "快报"}
        self.store.save("report", "json", data, date="2026-08-16")
        self.assertEqual(self.store.load("report", "json", "2026-08-16"), data)
        self.assertTrue(self.store.exists("report", "json", "2026-08-16"))

    def test_markdown_and_text_roundtrip(self):
        self.store.save("report", "markdown", "# 标题\n正文", date="2026-08-16")
        self.assertEqual(
            self.store.load("report", "markdown", "2026-08-16"), "# 标题\n正文"
        )
        self.store.save("note", "text", "plain", date="2026-08-16")
        self.assertEqual(self.store.load("note", "text", "2026-08-16"), "plain")

    def test_date_partitioning(self):
        self.store.save("r", "json", {}, date="2026-08-16")
        self.store.save("r", "json", {}, date="2026-08-17")
        # 不同日期独立
        self.assertTrue(self.store.exists("r", "json", "2026-08-16"))
        self.assertTrue(self.store.exists("r", "json", "2026-08-17"))
        self.assertIn("2026-08-16", str(self.store.resolve_path("r", "json", "2026-08-16")))

    def test_default_date_is_today_utc8(self):
        art = self.store.save("r", "json", {})
        today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
        self.assertIn(today, art.path.as_posix())

    def test_metadata_generation_and_persistence(self):
        art = self.store.save(
            "r", "json", {"a": 1}, date="2026-08-16", metadata={"source": "github"}
        )
        self.assertEqual(art.name, "r")
        self.assertEqual(art.type, "json")
        self.assertTrue(art.created_at)
        self.assertEqual(art.metadata, {"source": "github"})

        meta = self.store.load_metadata("r", "json", "2026-08-16")
        self.assertEqual(meta["name"], "r")
        self.assertEqual(meta["type"], "json")
        self.assertEqual(meta["metadata"], {"source": "github"})
        self.assertEqual(meta["created_at"], art.created_at)

    def test_exists_false_for_missing(self):
        self.assertFalse(self.store.exists("nope", "json", "2026-08-16"))

    def test_unsupported_type_raises(self):
        with self.assertRaises(ValueError):
            self.store.save("r", "yaml", {}, date="2026-08-16")
        with self.assertRaises(ValueError):
            self.store.load("r", "yaml", "2026-08-16")
        with self.assertRaises(ValueError):
            self.store.exists("r", "yaml", "2026-08-16")

    def test_load_missing_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.store.load("missing", "json", "2026-08-16")

    def test_load_metadata_missing_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.store.load_metadata("missing", "json", "2026-08-16")

    def test_invalid_json_raises(self):
        path = self.store.resolve_path("bad", "json", "2026-08-16")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{invalid json", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            self.store.load("bad", "json", "2026-08-16")


class TestStateStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "state" / "job_runs.jsonl"
        self.store = StateStore(self.path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_and_history(self):
        self.store.log_run(
            "github_trending",
            "success",
            start_time="2026-08-16T09:00:00+08:00",
            end_time="2026-08-16T09:05:00+08:00",
            artifacts=["trending.json", "summaries.json"],
        )
        self.store.log_run("feishu_report", "failed", artifacts=[])

        hist = self.store.history()
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[0]["job"], "github_trending")
        self.assertEqual(hist[0]["status"], "success")
        self.assertEqual(hist[0]["artifacts"], ["trending.json", "summaries.json"])
        self.assertEqual(hist[0]["start_time"], "2026-08-16T09:00:00+08:00")
        self.assertEqual(hist[1]["job"], "feishu_report")

    def test_history_empty_when_missing(self):
        self.assertEqual(self.store.history(), [])

    def test_default_times_generated(self):
        self.store.log_run("job", "success")
        rec = self.store.history()[0]
        self.assertTrue(rec["start_time"])
        self.assertTrue(rec["end_time"])

    def test_append_does_not_overwrite(self):
        self.store.log_run("a", "success")
        self.store.log_run("b", "success")
        self.assertEqual(len(self.store.history()), 2)


if __name__ == "__main__":
    unittest.main()
