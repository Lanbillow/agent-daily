import plistlib
import tempfile
import unittest
from pathlib import Path

from agent_daily.scheduler import (
    build_plist,
    install_jobs,
    job_label,
    parse_schedule,
    plist_filename,
    uninstall_jobs,
)


class TestScheduleParse(unittest.TestCase):
    def test_parse_0900(self):
        self.assertEqual(parse_schedule("09:00"), (9, 0))

    def test_parse_1000(self):
        self.assertEqual(parse_schedule("10:00"), (10, 0))

    def test_invalid_schedule_raises(self):
        with self.assertRaises(ValueError):
            parse_schedule("25:00")
        with self.assertRaises(ValueError):
            parse_schedule("not-a-time")


class TestLabel(unittest.TestCase):
    def test_job_label(self):
        self.assertEqual(job_label("github_trending"), "com.agent-daily.github-trending")
        self.assertEqual(job_label("feishu_report"), "com.agent-daily.feishu-report")

    def test_plist_filename(self):
        self.assertEqual(
            plist_filename("github_trending"), "com.agent-daily.github-trending.plist"
        )


class TestBuildPlist(unittest.TestCase):
    def _build(self, job_id="github_trending", schedule="09:00"):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # 创建模板（复制真实模板内容）
            real_tpl = Path(__file__).resolve().parents[1] / "scheduler" / "templates" / "com.agent-daily.job.plist.tpl"
            (root / "scheduler" / "templates").mkdir(parents=True)
            (root / "scheduler" / "templates" / "com.agent-daily.job.plist.tpl").write_text(
                real_tpl.read_text(encoding="utf-8"), encoding="utf-8"
            )
            xml = build_plist(job_id, schedule, root, "/usr/bin/uv", "/usr/bin:/bin", "/home/u")
            return plistlib.loads(xml.encode()), str(root)

    def test_program_arguments(self):
        data, _ = self._build()
        self.assertEqual(
            data["ProgramArguments"],
            ["/usr/bin/uv", "run", "agent-daily", "run", "github_trending"],
        )

    def test_working_directory(self):
        data, root = self._build()
        self.assertEqual(data["WorkingDirectory"], root)  # 固定为传入的 project_dir

    def test_calendar_interval(self):
        data, _ = self._build(schedule="09:00")
        self.assertEqual(data["StartCalendarInterval"], {"Hour": 9, "Minute": 0})

    def test_log_paths(self):
        data, _ = self._build()
        self.assertIn("data/logs/launchd/github_trending.stdout.log", data["StandardOutPath"])
        self.assertIn("data/logs/launchd/github_trending.stderr.log", data["StandardErrorPath"])

    def test_safety_fields(self):
        data, _ = self._build()
        self.assertEqual(data["ThrottleInterval"], 300)
        self.assertEqual(data["ProcessType"], "Background")
        self.assertTrue(data["LowPriorityIO"])


class TestInstallUninstall(unittest.TestCase):
    def _root_with_jobs(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "jobs").mkdir()
        (root / "jobs" / "github_trending.yaml").write_text(
            "job: github_trending\nschedule: '09:00'\nworkflow:\n  steps:\n    - {id: a, type: tool, tool: x, args: {}}\noutputs: []\n",
            encoding="utf-8",
        )
        # 复制模板
        real_tpl = Path(__file__).resolve().parents[1] / "scheduler" / "templates" / "com.agent-daily.job.plist.tpl"
        (root / "scheduler" / "templates").mkdir(parents=True)
        (root / "scheduler" / "templates" / "com.agent-daily.job.plist.tpl").write_text(
            real_tpl.read_text(encoding="utf-8"), encoding="utf-8"
        )
        return tmp, root

    def test_install_generates_plist(self):
        tmp, root = self._root_with_jobs()
        try:
            lad = Path(tmp.name) / "launchagents"
            results = install_jobs(project_dir=root, launch_agents_dir=lad)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["job"], "github_trending")
            plist = lad / "com.agent-daily.github-trending.plist"
            self.assertTrue(plist.exists())
            data = plistlib.loads(plist.read_bytes())
            self.assertEqual(data["ProgramArguments"][-1], "github_trending")
        finally:
            tmp.cleanup()

    def test_uninstall_removes_plist(self):
        tmp, root = self._root_with_jobs()
        try:
            lad = Path(tmp.name) / "launchagents"
            install_jobs(project_dir=root, launch_agents_dir=lad)
            removed = uninstall_jobs(project_dir=root, launch_agents_dir=lad)
            self.assertEqual(removed, ["github_trending"])
            self.assertFalse((lad / "com.agent-daily.github-trending.plist").exists())
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
