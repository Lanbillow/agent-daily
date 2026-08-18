"""数据解析层：HTML / JSON → Repo[]。

与 Source 严格分离：Source 返回原始响应，Parser 负责转换。

原则（禁止空结果伪装成功）：
  - 解析不到任何项目（HTML 结构变化 / JSON 为空）→ 抛 GithubParseError。
  - 非法 HTML/JSON / 缺关键字段 → 抛 GithubParseError。
  绝不返回空列表假装「今日暂无项目」。
"""

from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup

from .models import Repo


class GithubParseError(Exception):
    """解析层错误：非法响应 / 结构变化 / 空结果。"""


def parse(format_: str, text: str, base_url: str = "") -> list[Repo]:
    """按格式分派到 HTML/JSON 解析器。"""
    if format_ == "html":
        return parse_html(text, base_url=base_url)
    if format_ == "json":
        return parse_json(text)
    raise GithubParseError(f"不支持的解析格式：{format_!r}")


def parse_html(html: str, base_url: str = "") -> list[Repo]:
    """解析 GitHub trending 风格 HTML，返回 Repo 列表。"""
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("article.Box-row")
    if not articles:
        raise GithubParseError("未解析到任何项目（HTML 结构可能已变化）")

    repos: list[Repo] = []
    for article in articles:
        repos.append(_repo_from_html_article(article, base_url))
    return repos


def parse_json(text: str) -> list[Repo]:
    """解析 JSON（数组或含 items 的对象），返回 Repo 列表。"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GithubParseError(f"JSON 解析失败：{exc}") from exc

    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise GithubParseError("JSON 结构不是数组，且缺少 items 字段")
    if not items:
        raise GithubParseError("JSON 结果为空")

    repos: list[Repo] = []
    for item in items:
        repos.append(_repo_from_json(item))
    return repos


# -- HTML 解析辅助 -----------------------------------------------------
def _repo_from_html_article(article: Any, base_url: str) -> Repo:
    link = article.select_one("h2 a")
    if link is None:
        raise GithubParseError("HTML 条目缺少 h2 链接")

    href = (link.get("href") or "").strip()
    name = href.strip("/")
    if not name:
        name = " ".join(link.get_text().split())

    desc_el = article.select_one("p")
    description = desc_el.get_text(strip=True) if desc_el else ""

    lang_el = article.select_one("[itemprop=programmingLanguage]")
    language = lang_el.get_text(strip=True) if lang_el else ""

    stars_el = article.select_one("a[href$='/stargazers']")
    stars = _parse_stars(stars_el.get_text()) if stars_el else 0

    url = f"{base_url.rstrip('/')}/{name}" if base_url else name
    return Repo(name=name, description=description, language=language, stars=stars, url=url)


def _parse_stars(text: str) -> int:
    """解析 '1,234' / '12.3k' 形式的 star 数。"""
    t = text.strip().lower().replace(",", "")
    if t.endswith("k"):
        try:
            return int(float(t[:-1]) * 1000)
        except ValueError:
            return 0
    digits = "".join(c for c in t if c.isdigit())
    return int(digits) if digits else 0


# -- JSON 解析辅助 -----------------------------------------------------
def _repo_from_json(item: Any) -> Repo:
    if not isinstance(item, dict):
        raise GithubParseError(f"JSON 条目不是对象：{item!r}")

    name = item.get("name") or item.get("full_name")
    if not name:
        raise GithubParseError(f"JSON 条目缺少 name/full_name：{item!r}")

    stars = item.get("stars", item.get("stargazers_count", 0))
    return Repo(
        name=str(name),
        description=str(item.get("description") or ""),
        language=str(item.get("language") or ""),
        stars=int(stars or 0),
        url=str(item.get("url") or item.get("html_url") or ""),
    )
