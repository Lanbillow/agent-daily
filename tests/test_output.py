import tempfile
import unittest
from pathlib import Path

import httpx

from agent_daily.output import (
    FeishuProvider,
    LocalFileProvider,
    OutputError,
)


class TestLocalFile(unittest.TestCase):
    def test_write_creates_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = LocalFileProvider(tmp)
            path = provider.write("2026-08-16热点快报", "正文内容\n第二行")
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("# 2026-08-16热点快报", text)
            self.assertIn("正文内容", text)
            self.assertTrue(path.name.endswith(".md"))

    def test_write_same_title_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = LocalFileProvider(tmp)
            p1 = provider.write("快报", "内容A")
            p2 = provider.write("快报", "内容B")
            self.assertEqual(p1, p2)  # 同名文件，天然幂等
            self.assertIn("内容B", p2.read_text(encoding="utf-8"))


def _feishu_handler(calls, fail_create=False, http_error=None):
    """构造飞书 API 的 mock handler，记录调用顺序。"""

    def handler(request):
        path = request.url.path
        calls.append((request.method, path))
        if http_error:
            raise http_error
        if path.endswith("/tenant_access_token/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "tok-1"})
        if path.endswith("/documents") and request.method == "POST":
            if fail_create:
                return httpx.Response(200, json={"code": 10001, "msg": "创建失败"})
            return httpx.Response(
                200, json={"code": 0, "data": {"document": {"document_id": "doc-123"}}}
            )
        if "/children" in path:
            return httpx.Response(200, json={"code": 0, "data": {}})
        return httpx.Response(404, json={"code": 1, "msg": "not found"})

    return handler


def _provider(handler, record_path=None):
    client = httpx.Client(base_url="https://open.feishu.cn", transport=httpx.MockTransport(handler))
    return FeishuProvider("app-1", "secret-1", record_path=record_path, client=client)


class TestFeishu(unittest.TestCase):
    def test_token_create_write_sequence(self):
        calls = []
        provider = _provider(_feishu_handler(calls))
        doc_id = provider.write("标题", "第一段\n第二段")
        self.assertEqual(doc_id, "doc-123")
        paths = [p for _, p in calls]
        self.assertIn("/tenant_access_token/internal", paths[0])
        self.assertEqual(paths[1], "/open-apis/docx/v1/documents")
        self.assertIn("/children", paths[2])
        self.assertEqual(len(calls), 3)

    def test_missing_keys_raises(self):
        with self.assertRaises(OutputError):
            FeishuProvider("", "secret")
        with self.assertRaises(OutputError):
            FeishuProvider("app", "")

    def test_api_code_error_raises(self):
        calls = []
        provider = _provider(_feishu_handler(calls, fail_create=True))
        with self.assertRaises(OutputError):
            provider.write("标题", "内容")

    def test_http_error_raises(self):
        calls = []
        provider = _provider(_feishu_handler(calls, http_error=httpx.ConnectError("refused")))
        with self.assertRaises(OutputError):
            provider.write("标题", "内容")

    def test_idempotency_same_title_no_duplicate(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "records.json"
            provider = _provider(_feishu_handler(calls), record_path=str(record))
            id1 = provider.write("2026-08-16热点快报", "内容A")
            id2 = provider.write("2026-08-16热点快报", "内容B")
            self.assertEqual(id1, "doc-123")
            self.assertEqual(id2, "doc-123")
            # 只创建了一次文档（第二次直接命中幂等记录）
            create_count = sum(1 for _, p in calls if p == "/open-apis/docx/v1/documents")
            self.assertEqual(create_count, 1)

    def test_idempotency_persists_across_instances(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "records.json"
            handler = _feishu_handler(calls)
            p1 = _provider(handler, record_path=str(record))
            p1.write("2026-08-16热点快报", "内容A")

            # 新实例（模拟新的 launchd 进程）
            p2 = _provider(handler, record_path=str(record))
            id2 = p2.write("2026-08-16热点快报", "内容B")
            self.assertEqual(id2, "doc-123")
            create_count = sum(1 for _, p in calls if p == "/open-apis/docx/v1/documents")
            self.assertEqual(create_count, 1)


if __name__ == "__main__":
    unittest.main()
