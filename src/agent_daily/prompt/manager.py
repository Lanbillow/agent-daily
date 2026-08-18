"""PromptManager —— Prompt 独立文件管理。

Prompt 存于顶层 ``prompts/*.md``，采用 **Markdown + Front Matter** 格式：

    ---
    name: summarize_repo
    version: 1
    description: GitHub项目中文摘要
    variables:
      - repo_name
      - description
    ---
    正文 Markdown Prompt（可用 {{ repo_name }} 等变量）

变量校验（严格，禁止静默替换为空）：
  1. 模板声明 ``variables``。
  2. render 时传入变量不足 → 报错。
  3. 模板引用了未声明变量 → 报错。
  4. Jinja2 使用 StrictUndefined 兜底。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined, TemplateSyntaxError
from jinja2 import meta as jinja_meta


class PromptError(Exception):
    """Prompt 模块错误基类。"""


class PromptNotFoundError(PromptError):
    """Prompt 文件不存在。"""


class PromptParseError(PromptError):
    """Front Matter 解析 / 结构不合法。"""


class PromptVariableError(PromptError):
    """变量缺失或模板引用未声明变量。"""


@dataclass
class Prompt:
    """一个 Prompt（解析自 prompts/*.md）。"""

    name: str
    version: int
    description: str
    template_content: str
    variables: list[str] = field(default_factory=list)


class PromptManager:
    def __init__(
        self,
        prompts_dir: str | Path,
        env: Environment | None = None,
    ) -> None:
        self.prompts_dir = Path(prompts_dir)
        # StrictUndefined：任何未解析变量在渲染时抛错，绝不静默为空
        self.env = env or Environment(undefined=StrictUndefined)

    # -- loading ---------------------------------------------------------
    def load(self, name: str) -> Prompt:
        """按名加载 Prompt（读取 prompts/<name>.md 并解析）。"""
        path = self.prompts_dir / f"{name}.md"
        if not path.exists():
            raise PromptNotFoundError(f"Prompt 不存在：{path}")
        return self._parse(name, path.read_text(encoding="utf-8"), path)

    def _parse(self, name: str, text: str, source: Path) -> Prompt:
        meta, body = self._split_front_matter(text, source)

        fm_name = meta.get("name")
        if not fm_name:
            raise PromptParseError(f"Front Matter 缺少 name：{source}")
        if fm_name != name:
            raise PromptParseError(
                f"Front Matter name={fm_name!r} 与文件名 {name!r} 不一致：{source}"
            )

        version = meta.get("version")
        try:
            version = int(version) if version is not None else None
        except (TypeError, ValueError):
            raise PromptParseError(f"version 必须是整数：{source}") from None
        if version is None:
            raise PromptParseError(f"Front Matter 缺少 version：{source}")

        variables = meta.get("variables") or []
        if not isinstance(variables, list):
            raise PromptParseError(f"variables 必须是列表：{source}")

        return Prompt(
            name=name,
            version=version,
            description=str(meta.get("description", "")),
            template_content=body,
            variables=[str(v) for v in variables],
        )

    def _split_front_matter(self, text: str, source: Path) -> tuple[dict, str]:
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            raise PromptParseError(f"缺少 Front Matter（首行应为 ---）：{source}")

        fm_lines: list[str] = []
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            fm_lines.append(lines[i])
            i += 1
        if i >= len(lines):
            raise PromptParseError(f"Front Matter 缺少结束符 ---：{source}")

        body = "\n".join(lines[i + 1 :])
        try:
            meta = yaml.safe_load("\n".join(fm_lines)) or {}
        except yaml.YAMLError as exc:
            raise PromptParseError(f"Front Matter YAML 解析失败：{source} ({exc})") from exc
        if not isinstance(meta, dict):
            raise PromptParseError(f"Front Matter 必须是映射：{source}")
        return meta, body

    # -- rendering -------------------------------------------------------
    def render(self, name: str, **variables: Any) -> str:
        """加载并渲染 Prompt（严格变量校验后渲染）。"""
        prompt = self.load(name)
        return self._render(prompt, variables)

    def _render(self, prompt: Prompt, variables: dict[str, Any]) -> str:
        declared = set(prompt.variables)
        provided = set(variables)

        # 1) 模板语法检测
        try:
            ast = self.env.parse(prompt.template_content)
        except TemplateSyntaxError as exc:
            raise PromptError(
                f"模板语法错误：{prompt.name} 第 {exc.lineno} 行：{exc.message}"
            ) from exc

        # 2) 模板引用未声明变量
        referenced = jinja_meta.find_undeclared_variables(ast)
        undeclared = referenced - declared
        if undeclared:
            raise PromptVariableError(
                f"模板引用了未声明变量：{sorted(undeclared)}"
                f"（{prompt.name} 声明了 {sorted(declared)}）"
            )

        # 3) 传入变量不足
        missing = declared - provided
        if missing:
            raise PromptVariableError(
                f"缺少变量：{sorted(missing)}（{prompt.name}）"
            )

        # 4) 渲染（StrictUndefined 兜底，任何漏网之鱼都会抛错而非置空）
        template = self.env.from_string(prompt.template_content)
        return template.render(**variables)
