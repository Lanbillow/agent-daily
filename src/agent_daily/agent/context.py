"""执行上下文。

单次 workflow 运行的容器：{step_id: 步骤结果}。支持 ``${step_id.field}``
模板引用（字段/索引/属性路径），解析失败抛 ContextResolutionError（禁止静默）。

注意：只服务于单次运行，禁止跨任务持久化（跨任务数据走 storage/artifacts）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


class ContextResolutionError(Exception):
    """${...} 引用解析失败。"""


_REF = re.compile(r"\$\{([^}]+)\}")
_PATH_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


@dataclass
class ExecutionContext:
    data: dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def resolve(self, template: Any) -> Any:
        """解析模板中的 ${...} 引用。

        - 整串是单个 ``${...}`` 时返回原值（保留类型）。
        - 字符串内嵌时替换为字符串。
        - list/tuple/dict 递归解析。
        """
        if isinstance(template, str):
            m = _REF.fullmatch(template)
            if m:
                return self._lookup(m.group(1))
            return _REF.sub(lambda mo: _stringify(self._lookup(mo.group(1))), template)
        if isinstance(template, list):
            return [self.resolve(x) for x in template]
        if isinstance(template, tuple):
            return tuple(self.resolve(x) for x in template)
        if isinstance(template, dict):
            return {k: self.resolve(v) for k, v in template.items()}
        return template

    def _lookup(self, path: str) -> Any:
        tokens = _parse_path(path)
        if not tokens:
            raise ContextResolutionError(f"无法解析 ${{{path}}}：路径为空")

        value: Any = self.data
        for tok in tokens:
            value = _step(value, tok, path)
        return value


def _parse_path(path: str) -> list[Any]:
    tokens: list[Any] = []
    for m in _PATH_TOKEN.finditer(path):
        if m.group(1):
            tokens.append(m.group(1))
        else:
            tokens.append(int(m.group(2)))
    return tokens


def _step(value: Any, tok: Any, path: str) -> Any:
    if isinstance(tok, int):
        if isinstance(value, (list, tuple)) and 0 <= tok < len(value):
            return value[tok]
        raise ContextResolutionError(
            f"无法解析 ${{{path}}}：索引 {tok} 越界或目标非列表"
        )
    # str token
    if isinstance(value, dict):
        if tok in value:
            return value[tok]
        raise ContextResolutionError(f"无法解析 ${{{path}}}：键 {tok!r} 不存在")
    if hasattr(value, tok):
        return getattr(value, tok)
    raise ContextResolutionError(
        f"无法解析 ${{{path}}}：{type(value).__name__} 无字段 {tok!r}"
    )


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
