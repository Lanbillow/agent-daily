import unittest

from agent_daily.tools.report_composer import (
    ReportComposerTool,
    SummaryNormalizerTool,
    clean_summary,
)


class TestSummaryCleanup(unittest.TestCase):
    def test_removes_thinking_trace(self):
        raw = "<think>很长的内部推理</think>\n\n最终摘要：提供本地模型推理服务。"
        self.assertEqual(clean_summary(raw), "提供本地模型推理服务。")

    def test_unclosed_thinking_is_removed(self):
        self.assertEqual(clean_summary("<think>只有推理，没有答案"), "")

    def test_removes_repetitive_opening_and_metadata(self):
        text = "该项目是一个功能全面的下载管理器，使用TypeScript语言，支持53,958个星数。"
        self.assertEqual(clean_summary(text), "功能全面的下载管理器。")
        text = "该项目实现了一个现代Linux环境，使用Shell语言，包含26643个星号。"
        self.assertEqual(clean_summary(text), "现代Linux环境。")

    def test_normalizes_persisted_items(self):
        result = SummaryNormalizerTool().run({"items": [
            {"name": "x/y", "summary": "该项目提供一个本地多智能体框架。"}
        ]})
        self.assertTrue(result.success)
        self.assertEqual(result.data[0]["summary"], "本地多智能体框架。")


class TestReportComposer(unittest.TestCase):
    def test_every_project_is_included(self):
        items = [
            {"name": "a/one", "url": "https://x/one", "language": "Python", "stars": 10,
             "summary": "<think>ignore</think>第一个摘要。"},
            {"name": "b/two", "url": "https://x/two", "language": "Go", "stars": 20,
             "summary": "第二个摘要。"},
        ]
        result = ReportComposerTool().run({"date": "2026-08-19", "summaries": items})
        self.assertTrue(result.success)
        self.assertIn("[a/one](https://x/one)", result.data)
        self.assertIn("[b/two](https://x/two)", result.data)
        self.assertNotIn("<think>", result.data)
        self.assertIn("共收录 2 个", result.data)
        self.assertIn("今日观察", result.data)

    def test_empty_input_fails(self):
        result = ReportComposerTool().run({"date": "2026-08-19", "summaries": []})
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
