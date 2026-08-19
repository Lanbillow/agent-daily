"""数据源协议 + SourceAdapter + HTTP 抓取基类。

职责边界（Source 与 Parser 严格分离）：
  Source —— 只负责 HTTP 请求、URL 管理、网络异常处理，返回**原始响应**；
  Parser —— 负责 HTML/JSON → Repo[]（见 parser.py）。

Source 禁止做 HTML 解析 / JSON 转换 / Repo 生成。

所有 URL 必须来自 config.yaml（base_url + trending_path），禁止硬编码。
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from ...config.schema import GithubConfig

# 非 URL 常量：浏览器 User-Agent，避免被目标站拒绝
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class GithubSourceError(Exception):
    """数据源层错误：网络不可达 / HTTP 状态错误 / 源未配置 / 源不可用。"""


class TrendingSource(Protocol):
    """数据源协议：返回原始响应文本（不解析）。"""

    name: str
    format: str  # "html" | "json"
    base_url: str

    def fetch(self, since: str = "daily") -> str:
        """返回原始响应文本；失败抛 GithubSourceError。"""
        ...


class BaseHttpSource:
    """HTTP 抓取基类：URL 构建 + httpx + 超时/连接/状态码异常处理。"""

    def __init__(
        self,
        base_url: str,
        trending_path: str = "/trending",
        format_: str = "html",
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.trending_path = trending_path
        self.format = format_
        self._client = client or httpx.Client(
            timeout=timeout, headers={"User-Agent": DEFAULT_USER_AGENT}
        )

    def _build_url(self, since: str) -> str:
        return f"{self.base_url}{self.trending_path}?since={since}"

    def fetch(self, since: str = "daily") -> str:
        url = self._build_url(since)
        last_error: httpx.HTTPError | None = None
        for attempt in range(3):
            try:
                resp = self._client.get(url)
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < 2:
                    continue
                raise GithubSourceError(f"请求超时（已重试 3 次）：{url}") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < 2:
                    continue
                raise GithubSourceError(f"连接失败（已重试 3 次）：{exc}") from exc

            if resp.status_code == 200:
                return resp.text
            if resp.status_code < 500 or attempt == 2:
                raise GithubSourceError(f"返回 HTTP {resp.status_code}：{url}")

        # Defensive fallback; every loop branch above returns or raises.
        raise GithubSourceError(f"连接失败（已重试 3 次）：{last_error}")


class SourceAdapter:
    """根据 github.source.provider 选择数据源（地址全部来自 config）。

    若 provider 未配置 / base_url 为空，直接抛 GithubSourceError，
    禁止静默切换。
    """

    def __init__(self, config: GithubConfig) -> None:
        self.config = config

    def get_source(self) -> TrendingSource:
        provider = self.config.source.provider
        providers = self.config.providers or {}
        if provider not in providers:
            raise GithubSourceError(
                f"未知数据源 provider：{provider!r}（可用：{sorted(providers)}）"
            )

        cfg: dict[str, Any] = providers[provider] or {}
        base_url = str(cfg.get("base_url", "") or "").strip()
        if not base_url:
            raise GithubSourceError(
                f"数据源 {provider!r} 未配置 base_url"
                f"（config.yaml: github.providers.{provider}.base_url）"
            )

        trending_path = cfg.get("trending_path", "/trending")
        format_ = cfg.get("format", "html")
        timeout = self.config.timeout_seconds

        if provider == "official":
            from .official import GitHubOfficialSource

            return GitHubOfficialSource(base_url, trending_path, format_, timeout)
        if provider == "mirror":
            from .mirror import GitHubMirrorSource

            return GitHubMirrorSource(base_url, trending_path, format_, timeout)
        raise GithubSourceError(f"未实现的数据源 provider：{provider!r}")
