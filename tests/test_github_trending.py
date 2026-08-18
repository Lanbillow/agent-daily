import json
import unittest
from pathlib import Path
from unittest import mock

import httpx

from agent_daily.config.schema import GithubConfig, GithubSourceConfig
from agent_daily.tools.github_trending import (
    GithubParseError,
    GithubSourceError,
    GithubTrendingTool,
    SourceAdapter,
    parse_html,
    parse_json,
)
from agent_daily.tools.github_trending.models import Repo
from agent_daily.tools.github_trending.official import GitHubOfficialSource
from agent_daily.tools.github_trending.mirror import GitHubMirrorSource


def _html_sample(repos):
    arts = []
    for r in repos:
        arts.append(
            f"""
<article class="Box-row">
  <h2 class="h3 lh-condensed"><a href="/{r['name']}">{r['name']}</a></h2>
  <p class="col-9 color-fg-muted my-1 pr-4">{r['description']}</p>
  <div class="f6 color-fg-muted mt-2">
    <span itemprop="programmingLanguage">{r['language']}</span>
    <a href="/{r['name']}/stargazers">{r['stars']}</a>
  </div>
</article>"""
        )
    return "<div class='Box'>" + "".join(arts) + "</div>"


SAMPLE_REPOS = [
    {"name": "owner/repo1", "description": "项目一", "language": "Python", "stars": "1,234"},
    {"name": "owner/repo2", "description": "项目二", "language": "Go", "stars": "567"},
]


class TestHtmlParse(unittest.TestCase):
    def test_html_sample_parse(self):
        repos = parse_html(_html_sample(SAMPLE_REPOS), base_url="https://m.example.com")
        self.assertEqual(len(repos), 2)
        self.assertIsInstance(repos[0], Repo)
        self.assertEqual(repos[0].name, "owner/repo1")
        self.assertEqual(repos[0].description, "项目一")
        self.assertEqual(repos[0].language, "Python")
        self.assertEqual(repos[0].stars, 1234)
        self.assertEqual(repos[0].url, "https://m.example.com/owner/repo1")
        self.assertEqual(repos[1].stars, 567)


class TestJsonParse(unittest.TestCase):
    def test_json_sample_parse(self):
        text = json.dumps(
            {
                "items": [
                    {"full_name": "a/b", "description": "x", "language": "Rust",
                     "stargazers_count": 100, "html_url": "https://github.com/a/b"},
                    {"name": "c/d", "description": "y", "language": "JS",
                     "stars": 50, "url": "https://x/c/d"},
                ]
            }
        )
        repos = parse_json(text)
        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0].name, "a/b")
        self.assertEqual(repos[0].stars, 100)
        self.assertEqual(repos[0].url, "https://github.com/a/b")
        self.assertEqual(repos[1].name, "c/d")
        self.assertEqual(repos[1].stars, 50)


class TestSourceParserSeparation(unittest.TestCase):
    def test_source_returns_raw_parser_converts(self):
        html = _html_sample(SAMPLE_REPOS)

        def handler(request):
            return httpx.Response(200, text=html)

        client = httpx.Client(
            base_url="https://m.example.com", transport=httpx.MockTransport(handler)
        )
        source = GitHubOfficialSource("https://m.example.com", "/trending", "html", 5.0, client=client)
        raw = source.fetch("daily")
        # Source 返回原始字符串，不做转换
        self.assertIsInstance(raw, str)
        self.assertIn("Box-row", raw)
        # Parser 负责转换
        repos = parse_html(raw)
        self.assertIsInstance(repos[0], Repo)


class TestProviderSwitch(unittest.TestCase):
    def _config(self, provider):
        return GithubConfig(
            source=GithubSourceConfig(provider=provider),
            providers={
                "official": {"base_url": "https://github.com"},
                "mirror": {"base_url": "https://m.example.com"},
            },
        )

    def test_official_selected(self):
        src = SourceAdapter(self._config("official")).get_source()
        self.assertIsInstance(src, GitHubOfficialSource)
        self.assertEqual(src.name, "official")

    def test_mirror_selected(self):
        src = SourceAdapter(self._config("mirror")).get_source()
        self.assertIsInstance(src, GitHubMirrorSource)
        self.assertEqual(src.name, "mirror")

    def test_unknown_provider_raises(self):
        with self.assertRaises(GithubSourceError):
            SourceAdapter(self._config("nope")).get_source()

    def test_mirror_unconfigured_raises(self):
        cfg = GithubConfig(
            source=GithubSourceConfig(provider="mirror"),
            providers={"mirror": {"base_url": ""}},
        )
        with self.assertRaises(GithubSourceError):
            SourceAdapter(cfg).get_source()


class TestUrlFromConfig(unittest.TestCase):
    def test_no_hardcoded_url_in_code(self):
        import re

        pkg = (
            Path(__file__).resolve().parents[1]
            / "src" / "agent_daily" / "tools" / "github_trending"
        )
        pattern = re.compile(r"github\.com|https?://")
        offenders = []
        for py in pkg.glob("*.py"):
            for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line):
                    offenders.append(f"{py.name}:{i}: {line.strip()}")
        self.assertEqual(offenders, [], "发现硬编码 URL：" + "; ".join(offenders))

    def test_url_built_from_config(self):
        captured = {}

        def handler(request):
            captured["url"] = str(request.url)
            return httpx.Response(200, text=_html_sample(SAMPLE_REPOS))

        client = httpx.Client(transport=httpx.MockTransport(handler))
        source = GitHubMirrorSource("https://my-mirror.example.com", "/trending", "html", 5.0, client=client)
        source.fetch("weekly")
        self.assertTrue(captured["url"].startswith("https://my-mirror.example.com/trending"))
        self.assertIn("since=weekly", captured["url"])


class TestNetworkExceptions(unittest.TestCase):
    def _source(self, handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        return GitHubOfficialSource("https://m.example.com", "/trending", "html", 5.0, client=client)

    def test_timeout_raises(self):
        def handler(request):
            raise httpx.TimeoutException("timeout")

        with self.assertRaises(GithubSourceError):
            self._source(handler).fetch()

    def test_http_500_raises(self):
        def handler(request):
            return httpx.Response(500, text="error")

        with self.assertRaises(GithubSourceError):
            self._source(handler).fetch()

    def test_connection_error_raises(self):
        def handler(request):
            raise httpx.ConnectError("connection refused")

        with self.assertRaises(GithubSourceError):
            self._source(handler).fetch()


class TestParseExceptions(unittest.TestCase):
    def test_parse_html_no_articles_raises(self):
        with self.assertRaises(GithubParseError):
            parse_html("<html><body>nothing here</body></html>")

    def test_parse_html_garbage_raises(self):
        with self.assertRaises(GithubParseError):
            parse_html("definitely not html")

    def test_parse_json_invalid_raises(self):
        with self.assertRaises(GithubParseError):
            parse_json("{invalid json")

    def test_parse_json_empty_array_raises(self):
        with self.assertRaises(GithubParseError):
            parse_json("[]")


class TestTool(unittest.TestCase):
    def test_tool_run_success(self):
        class FakeSource:
            name = "mirror"
            format = "html"
            base_url = "https://m.example.com"

            def fetch(self, since="daily"):
                return _html_sample(SAMPLE_REPOS)

        adapter = mock.MagicMock()
        adapter.get_source.return_value = FakeSource()
        tool = GithubTrendingTool(adapter)
        result = tool.run({"since": "daily", "limit": 1})
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0]["name"], "owner/repo1")

    def test_tool_run_failure_propagates(self):
        cfg = GithubConfig(
            source=GithubSourceConfig(provider="mirror"),
            providers={"mirror": {"base_url": ""}},
        )
        tool = GithubTrendingTool(SourceAdapter(cfg))
        with self.assertRaises(GithubSourceError):
            tool.run({})


if __name__ == "__main__":
    unittest.main()
