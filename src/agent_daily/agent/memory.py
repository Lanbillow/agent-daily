"""Memory 接口（暂不实现，仅保留扩展点）。

第一阶段固定使用 NullMemory（不持久化任何上下文）；未来第二阶段再实现
真实 Memory（会话记忆 / 长期记忆），接口保持不变。
"""

from __future__ import annotations

from typing import Any, Protocol


class Memory(Protocol):
    """记忆协议（预留扩展）。"""

    def load_context(self) -> dict[str, Any]:
        """读取持久化上下文。"""
        ...

    def save_context(self, context: dict[str, Any]) -> None:
        """写入上下文。"""
        ...


class NullMemory:
    """默认实现：不读写任何内容。"""

    def load_context(self) -> dict[str, Any]:
        return {}

    def save_context(self, context: dict[str, Any]) -> None:
        return None
