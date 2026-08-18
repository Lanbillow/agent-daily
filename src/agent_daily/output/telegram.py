"""TelegramProvider —— 预留输出通道（暂不实现）。"""

from __future__ import annotations

from typing import Any


class TelegramProvider:
    name = "telegram"

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def write(self, title: str, content: str, **kwargs: Any) -> Any:
        raise NotImplementedError("TelegramProvider.write 预留，暂不实现")
