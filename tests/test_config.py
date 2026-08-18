import tempfile
import unittest
from pathlib import Path

from agent_daily.config.loader import load_config, load_secrets
from agent_daily.config.schema import Settings


class TestLoadConfig(unittest.TestCase):
    def test_defaults_when_missing(self):
        cfg = load_config("/nonexistent/config.yaml")
        self.assertIsInstance(cfg, Settings)
        self.assertEqual(cfg.model.primary, "local")
        self.assertEqual(cfg.timezone, "Asia/Shanghai")

    def test_merge_overrides_known_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.yaml"
            p.write_text(
                """
timezone: UTC
model:
  primary: deepseek
  local:
    cwd: "../other-mlx"
github:
  source:
    provider: official
  providers:
    mirror:
      base_url: "https://example.com"
    """
            )
            cfg = load_config(p)
            self.assertEqual(cfg.timezone, "UTC")
            self.assertEqual(cfg.model.primary, "deepseek")
            self.assertEqual(cfg.model.local.cwd, "../other-mlx")
            self.assertEqual(cfg.github.source.provider, "official")
            self.assertEqual(cfg.github.providers["mirror"]["base_url"], "https://example.com")
            # 未覆盖字段保持默认
            self.assertEqual(cfg.model.fallback, "deepseek")

    def test_invalid_yaml_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.yaml"
            p.write_text("::not-valid-yaml::")
            cfg = load_config(p)
            self.assertEqual(cfg.model.primary, "local")


class TestLoadSecrets(unittest.TestCase):
    def test_parse_key_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "secrets.env"
            p.write_text(
                "# comment\nDEEPSEEK_API_KEY=sk-abc\nFEISHU_APP_ID=\"cli_123\"\n\n"
            )
            s = load_secrets(p)
            self.assertEqual(s["DEEPSEEK_API_KEY"], "sk-abc")
            self.assertEqual(s["FEISHU_APP_ID"], "cli_123")

    def test_missing_returns_empty(self):
        self.assertEqual(load_secrets("/nonexistent/secrets.env"), {})


if __name__ == "__main__":
    unittest.main()
