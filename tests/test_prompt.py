import tempfile
import unittest
from pathlib import Path

from agent_daily.prompt import (
    PromptManager,
    PromptNotFoundError,
    PromptParseError,
    PromptVariableError,
)

_FM = """---
name: {name}
version: {version}
description: {desc}
variables:
{var_list}---
"""


def _write_prompt(directory: Path, name: str, body: str, variables: list[str], version=1, desc="测试"):
    var_lines = "".join(f"  - {v}\n" for v in variables)
    fm = _FM.format(name=name, version=version, desc=desc, var_list=var_lines)
    (directory / f"{name}.md").write_text(fm + body, encoding="utf-8")


class TestPromptLoad(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)
        self.mgr = PromptManager(self.d)

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_parses_front_matter(self):
        _write_prompt(self.d, "t", "正文 {{ x }}", ["x"])
        p = self.mgr.load("t")
        self.assertEqual(p.name, "t")
        self.assertEqual(p.version, 1)
        self.assertEqual(p.description, "测试")
        self.assertEqual(p.variables, ["x"])
        self.assertIn("{{ x }}", p.template_content)

    def test_load_not_found(self):
        with self.assertRaises(PromptNotFoundError):
            self.mgr.load("missing")

    def test_front_matter_missing(self):
        (self.d / "t.md").write_text("没有 front matter", encoding="utf-8")
        with self.assertRaises(PromptParseError):
            self.mgr.load("t")

    def test_name_mismatch(self):
        _write_prompt(self.d, "file_name", "正文", [])
        # front matter name 是 "file_name"，与文件同名；改写成不匹配
        (self.d / "other.md").write_text(
            "---\nname: wrong\nversion: 1\n---\n正文", encoding="utf-8"
        )
        with self.assertRaises(PromptParseError):
            self.mgr.load("other")


class TestPromptRender(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)
        self.mgr = PromptManager(self.d)

    def tearDown(self):
        self._tmp.cleanup()

    def test_render_success(self):
        _write_prompt(self.d, "t", "你好 {{ thing }}，{{ n }} 个", ["thing", "n"])
        out = self.mgr.render("t", thing="世界", n=3)
        self.assertEqual(out, "你好 世界，3 个")

    def test_missing_variable_fails(self):
        _write_prompt(self.d, "t", "{{ a }}{{ b }}", ["a", "b"])
        with self.assertRaises(PromptVariableError) as cm:
            self.mgr.render("t", a=1)  # 缺 b
        self.assertIn("b", str(cm.exception))

    def test_undeclared_variable_fails(self):
        # 模板引用了 {{ extra }}，但 variables 未声明
        _write_prompt(self.d, "t", "{{ declared }} {{ extra }}", ["declared"])
        with self.assertRaises(PromptVariableError) as cm:
            self.mgr.render("t", declared=1, extra=2)
        self.assertIn("extra", str(cm.exception))

    def test_template_syntax_error(self):
        _write_prompt(self.d, "t", "{{ broken", ["broken"])
        with self.assertRaises(Exception):
            self.mgr.render("t", broken=1)


class TestInitTemplates(unittest.TestCase):
    def test_real_templates_are_valid(self):
        prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
        mgr = PromptManager(prompts_dir)

        p1 = mgr.load("summarize_repo")
        self.assertEqual(p1.variables, ["repo_name", "description", "language", "stars"])

        p2 = mgr.load("compose_report")
        self.assertEqual(p2.variables, ["date", "summaries"])

        # 真实模板能成功渲染
        out = mgr.render(
            "summarize_repo",
            repo_name="demo", description="一个示例", language="Python", stars=100,
        )
        self.assertIn("demo", out)
        self.assertIn("Python", out)


if __name__ == "__main__":
    unittest.main()
