import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx

from agent_daily.config.schema import DeepSeekConfig, LocalModelConfig
from agent_daily.model import (
    DeepSeekProvider,
    LocalMLXProvider,
    ModelAPIError,
    ModelError,
    ModelLoadError,
    ModelManager,
    ModelProcessError,
    ModelTimeoutError,
)


class FakeProvider:
    """ModelManager 测试用的假 provider。"""

    def __init__(self, name, result=None, error=None):
        self.name = name
        self.result = result
        self.error = error

    def chat(self, messages, **kwargs):
        if self.error:
            raise self.error
        return self.result


class TestModelManager(unittest.TestCase):
    def test_local_success(self):
        mgr = ModelManager(FakeProvider("local", result="本地结果"))
        self.assertEqual(mgr.chat([{"role": "user", "content": "hi"}]), "本地结果")

    def test_local_fail_deepseek_fallback(self):
        primary = FakeProvider("local", error=ModelProcessError("本地挂了"))
        fallback = FakeProvider("deepseek", result="远端结果")
        mgr = ModelManager(primary, fallback)
        self.assertEqual(mgr.chat([]), "远端结果")

    def test_both_fail_raises(self):
        mgr = ModelManager(
            FakeProvider("local", error=ModelLoadError("x")),
            FakeProvider("deepseek", error=ModelAPIError("y")),
        )
        with self.assertRaises(ModelError):
            mgr.chat([])

    def test_no_fallback_reraises_primary_error(self):
        mgr = ModelManager(FakeProvider("local", error=ModelProcessError("挂了")))
        with self.assertRaises(ModelProcessError):
            mgr.chat([])

    def test_call_logging(self):
        import logging

        with self.assertLogs("agent_daily.model", level="INFO") as cm:
            mgr = ModelManager(FakeProvider("local", result="ok"))
            mgr.chat([])
        joined = "\n".join(cm.output)
        self.assertIn("provider=local", joined)
        self.assertIn("success=true", joined)
        self.assertIn("duration=", joined)


class TestLocalMLXProvider(unittest.TestCase):
    def _provider(self, tmp, command=("echo",)):
        config = LocalModelConfig(cwd=tmp, command=list(command), timeout_seconds=5)
        return LocalMLXProvider(config, project_root=None)

    def test_subprocess_success_and_prompt_assembly(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = self._provider(tmp)
            fake = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="  你好世界  \n", stderr=""
            )
            with mock.patch("agent_daily.model.local.subprocess.run", return_value=fake) as m:
                out = provider.chat(
                    [
                        {"role": "system", "content": "你是助手"},
                        {"role": "user", "content": "你好"},
                    ]
                )
            self.assertEqual(out, "你好世界")
            cmd = m.call_args[0][0]
            self.assertIn("--prompt", cmd)
            self.assertIn("你好", cmd)
            self.assertIn("--system", cmd)
            self.assertIn("你是助手", cmd)

    def test_timeout_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = self._provider(tmp)
            exc = subprocess.TimeoutExpired(cmd="uv", timeout=5)
            with mock.patch("agent_daily.model.local.subprocess.run", side_effect=exc):
                with self.assertRaises(ModelTimeoutError):
                    provider.chat([{"role": "user", "content": "hi"}])

    def test_nonzero_exit_raises_process_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = self._provider(tmp)
            fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="model not found")
            with mock.patch("agent_daily.model.local.subprocess.run", return_value=fake):
                with self.assertRaises(ModelProcessError):
                    provider.chat([{"role": "user", "content": "hi"}])

    def test_missing_cwd_raises_load_error(self):
        config = LocalModelConfig(cwd="/nonexistent/mlx-dir", command=["echo"])
        provider = LocalMLXProvider(config, project_root=None)
        with self.assertRaises(ModelLoadError):
            provider.chat([{"role": "user", "content": "hi"}])


class TestDeepSeekProvider(unittest.TestCase):
    def _config(self):
        return DeepSeekConfig(model="deepseek-chat", base_url="https://api.deepseek.com")

    def test_missing_api_key_raises(self):
        with self.assertRaises(ModelAPIError):
            DeepSeekProvider(self._config(), "")

    def test_api_call_success(self):
        def handler(request):
            return httpx.Response(
                200, json={"choices": [{"message": {"content": "你好"}}]}
            )

        client = httpx.Client(
            base_url="https://api.deepseek.com", transport=httpx.MockTransport(handler)
        )
        provider = DeepSeekProvider(self._config(), "sk-test", client=client)
        out = provider.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(out, "你好")

    def test_api_error_status(self):
        def handler(request):
            return httpx.Response(500, text="server error")

        client = httpx.Client(
            base_url="https://api.deepseek.com", transport=httpx.MockTransport(handler)
        )
        provider = DeepSeekProvider(self._config(), "sk-test", client=client)
        with self.assertRaises(ModelAPIError):
            provider.chat([{"role": "user", "content": "hi"}])


class TestNoMlxImport(unittest.TestCase):
    def test_no_mlx_import_in_agent_daily(self):
        """静态检查：agent_daily 内禁止 import mlx / mlx_lm。"""
        import re

        src = Path(__file__).resolve().parents[1] / "src" / "agent_daily"
        pattern = re.compile(r"^\s*(?:import|from)\s+mlx(?:_lm)?\b")
        offenders = []
        for py in src.rglob("*.py"):
            for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line):
                    offenders.append(f"{py}:{i}: {line.strip()}")
        self.assertEqual(offenders, [], "发现 mlx/mlx_lm import：" + "; ".join(offenders))


if __name__ == "__main__":
    unittest.main()
