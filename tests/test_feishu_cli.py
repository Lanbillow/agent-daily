import json
import subprocess
import unittest
from unittest import mock

from agent_daily.output import FeishuCLIProvider, OutputError, OutputRegistry
from agent_daily.output.local_file import LocalFileProvider


def _success_stdout(token="boxcn123"):
    return json.dumps({
        "ok": True,
        "identity": "user",
        "data": {"file_token": token, "file_name": "x.md", "size_bytes": 1},
    })


class TestFeishuCLIProvider(unittest.TestCase):
    def setUp(self):
        self.provider = FeishuCLIProvider(command="lark-cli", timeout_seconds=120)

    def test_success_returns_file_token(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=_success_stdout(), stderr="")
        with mock.patch("subprocess.run", return_value=fake) as m:
            result = self.provider.write("快报", "正文")
        self.assertEqual(result, "boxcn123")

    def test_command_and_stdin(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=_success_stdout(), stderr="")
        with mock.patch("subprocess.run", return_value=fake) as m:
            self.provider.write("快报", "hello\nworld")
        cmd = m.call_args[0][0]
        self.assertEqual(cmd[:3], ["lark-cli", "markdown", "+create"])
        self.assertIn("-", cmd)  # --content -（stdin）
        # stdin 内容正确传递
        self.assertEqual(m.call_args[1]["input"], "hello\nworld")

    def test_title_converts_to_name_md(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=_success_stdout(), stderr="")
        with mock.patch("subprocess.run", return_value=fake) as m:
            self.provider.write("2026-08-16热点快报", "x")
        cmd = m.call_args[0][0]
        name_idx = cmd.index("--name") + 1
        self.assertEqual(cmd[name_idx], "2026-08-16热点快报.md")

    def test_nonzero_exit_raises(self):
        fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="boom")
        with mock.patch("subprocess.run", return_value=fake):
            with self.assertRaises(OutputError):
                self.provider.write("t", "c")

    def test_timeout_raises(self):
        exc = subprocess.TimeoutExpired(cmd="lark-cli", timeout=120)
        with mock.patch("subprocess.run", side_effect=exc):
            with self.assertRaises(OutputError):
                self.provider.write("t", "c")

    def test_missing_command_raises(self):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError()):
            with self.assertRaises(OutputError):
                self.provider.write("t", "c")

    def test_invalid_stdout_raises(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="not json", stderr="")
        with mock.patch("subprocess.run", return_value=fake):
            with self.assertRaises(OutputError):
                self.provider.write("t", "c")

    def test_ok_false_raises(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"ok": False, "error": {"msg": "x"}}), stderr=""
        )
        with mock.patch("subprocess.run", return_value=fake):
            with self.assertRaises(OutputError):
                self.provider.write("t", "c")


class TestRegistryDefault(unittest.TestCase):
    def test_get_falls_back_to_default(self):
        reg = OutputRegistry()
        reg.register(LocalFileProvider("/tmp"))
        reg.register(FeishuCLIProvider())
        reg.set_default("feishu_cli")
        # "feishu" 未注册 → 回退到默认 feishu_cli
        self.assertEqual(reg.get("feishu").name, "feishu_cli")
        # 显式注册的名字直接命中
        self.assertEqual(reg.get("local_file").name, "local_file")

    def test_get_raises_without_default(self):
        reg = OutputRegistry()
        reg.register(LocalFileProvider("/tmp"))
        with self.assertRaises(KeyError):
            reg.get("feishu")


if __name__ == "__main__":
    unittest.main()
