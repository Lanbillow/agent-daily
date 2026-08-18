"""模型执行层统一接口。

所有模型提供者（本地 MLX / 远端 DeepSeek）实现同一接口，上层只依赖
`ModelProvider`，不感知具体引擎。
"""

from __future__ import annotations

from typing import Any, Protocol


class ModelProvider(Protocol):
    """模型提供者协议。"""

    name: str

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """给定对话消息列表，返回模型生成的文本。

        Args:
            messages: [{"role": "system"|"user"|"assistant", "content": ...}, ...]
            **kwargs: 生成参数（max_tokens / temperature 等），由实现决定是否支持。

        Returns:
            模型输出的完整文本。
        """
        ...
