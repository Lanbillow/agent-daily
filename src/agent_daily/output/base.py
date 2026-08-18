"""输出抽象层统一接口。

OutputProvider 是「内容输出」的统一抽象。Job 不直接调用外部 API，必须经
Agent → OutputProvider → 具体 Provider（LocalFile / Feishu / ...）。

失败原则：输出失败必须抛 OutputError，禁止「空成功」。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Protocol

log = logging.getLogger("agent_daily.output")


class OutputError(Exception):
    """输出层错误（本地写失败 / 飞书 API 失败 / 缺密钥等）。"""


class OutputProvider(Protocol):
    """输出提供者协议。"""

    name: str

    def write(self, title: str, content: str, **kwargs: Any) -> Any:
        """以 title 为标题输出 content，返回标识（document_id / 文件路径）。"""
        ...


class IdempotencyRecord:
    """幂等记录：key → 标识，持久化到 JSON 文件（跨进程去重）。

    用于自动任务重复执行时避免无限创建重复输出（如飞书文档）。
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def get(self, key: str) -> str | None:
        return self._load().get(key)

    def set(self, key: str, identifier: str) -> None:
        data = self._load()
        data[key] = identifier
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("幂等记录文件损坏，忽略：%s（%s）", self.path, exc)
            return {}
        return data if isinstance(data, dict) else {}


class OutputRegistry:
    """输出提供者注册表（容器 + 默认提供者回退）。

    ``set_default(name)`` 后，``get(name)`` 在请求的名字未注册时回退到默认
    提供者（用于「provider 未显式配置时走 config 的 output.default」）。
    """

    def __init__(self) -> None:
        self._providers: dict[str, OutputProvider] = {}
        self.default_name: str | None = None

    def register(self, provider: OutputProvider) -> None:
        self._providers[provider.name] = provider

    def set_default(self, name: str) -> None:
        self.default_name = name

    def get(self, name: str) -> OutputProvider:
        if name in self._providers:
            return self._providers[name]
        if self.default_name and self.default_name in self._providers:
            return self._providers[self.default_name]
        raise KeyError(f"未注册的输出提供者：{name}")

    def names(self) -> list[str]:
        return list(self._providers.keys())
