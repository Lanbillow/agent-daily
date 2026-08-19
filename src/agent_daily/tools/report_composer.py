"""Deterministic Markdown report composition for small-model summaries."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .base import ToolResult

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_OPEN = re.compile(r"<think>.*", re.IGNORECASE | re.DOTALL)
_LEADING_NOISE = re.compile(
    r"^(?:最终摘要|摘要|中文摘要|输出)\s*[：:]\s*", re.IGNORECASE
)
_GENERIC_OPENING = re.compile(
    r"^该项目(?:是一个|是一款|实现了一个|实现一个|提供一个|提供一款|提供|用于构建一个|用于构建|用于)"
)
_REPEATED_METADATA = re.compile(
    r"，(?:使用|采用)[^，。]{1,30}语言，(?:支持|拥有|包含)?[\d,]+个?(?:星数|星号|Star|Stars)",
    re.IGNORECASE,
)


def clean_summary(value: Any) -> str:
    """Remove reasoning traces and common answer wrappers from model output."""
    text = str(value or "").strip()
    text = _THINK_BLOCK.sub("", text).strip()
    text = _THINK_OPEN.sub("", text).strip()
    text = _LEADING_NOISE.sub("", text).strip()
    text = _GENERIC_OPENING.sub("", text).strip()
    text = _REPEATED_METADATA.sub("", text)
    text = text.strip("` \n\t\"'“”")
    lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
    return " ".join(lines).strip()


class SummaryNormalizerTool:
    """Normalize every model summary before it is persisted or composed."""

    name = "normalize_summaries"
    description = "清除摘要中的思考过程、模板化开头和重复元数据"
    parameters = {"type": "object", "properties": {"items": {"type": "array"}}}

    def run(self, args: dict[str, Any]) -> ToolResult:
        items = args.get("items")
        if not isinstance(items, list):
            return ToolResult(success=False, error="items 必须是列表")
        normalized = []
        for item in items:
            if not isinstance(item, dict):
                continue
            entry = dict(item)
            summary = clean_summary(entry.get("summary"))
            entry["summary"] = summary or clean_summary(entry.get("description"))
            normalized.append(entry)
        return ToolResult(success=True, data=normalized)


class ReportComposerTool:
    """Compose a complete report without another lossy model generation pass."""

    name = "compose_report"
    description = "将项目摘要确定性组装为完整 Markdown 热点快报"
    parameters = {
        "type": "object",
        "properties": {
            "date": {"type": "string"},
            "summaries": {"type": "array"},
        },
        "required": ["date", "summaries"],
    }

    def run(self, args: dict[str, Any]) -> ToolResult:
        summaries = args.get("summaries")
        if not isinstance(summaries, list) or not summaries:
            return ToolResult(success=False, error="summaries 必须是非空列表")

        sections = [f"共收录 {len(summaries)} 个 GitHub 热门项目。"]
        languages: Counter[str] = Counter()
        top_name = ""
        top_stars = -1

        for item in summaries:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "未命名项目")
            url = str(item.get("url") or "")
            language = str(item.get("language") or "未知")
            try:
                stars = int(item.get("stars") or 0)
            except (TypeError, ValueError):
                stars = 0
            summary = clean_summary(item.get("summary"))
            if not summary:
                summary = clean_summary(item.get("description")) or "暂无项目描述。"

            languages[language] += 1
            if stars > top_stars:
                top_name, top_stars = name, stars
            heading = f"## [{name}]({url})" if url else f"## {name}"
            sections.append(
                f"{heading}\n\n{summary}\n\n"
                f"- 主要语言：{language}\n- Star 数：{stars:,}"
            )

        language_text = "、".join(name for name, _ in languages.most_common(3))
        observation = f"今日项目主要集中在 {language_text} 生态"
        if top_name:
            observation += f"；其中 {top_name} 以 {top_stars:,} Star 关注度最高"
        sections.append(f"## 今日观察\n\n{observation}。")
        return ToolResult(success=True, data="\n\n".join(sections) + "\n")
