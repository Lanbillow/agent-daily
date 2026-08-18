import tempfile
import unittest
from pathlib import Path

from agent_daily.doctor import (
    check_config_file,
    check_data_writable,
    check_mlxsvc,
    check_python_version,
)


class TestDoctor(unittest.TestCase):
    def test_python_version_ok(self):
        r = check_python_version()
        self.assertEqual(r.status, "OK")

    def test_config_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.yaml"
            p.write_text("timezone: UTC")
            self.assertEqual(check_config_file(p).status, "OK")
            self.assertEqual(check_config_file(Path(tmp) / "missing.yaml").status, "WARN")

    def test_mlxsvc_missing_is_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = check_mlxsvc(Path(tmp) / "no-such-dir")
            self.assertEqual(r.status, "FAIL")

    def test_data_writable(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "data"
            self.assertEqual(check_data_writable(d).status, "OK")
            self.assertTrue(d.exists())


if __name__ == "__main__":
    unittest.main()
