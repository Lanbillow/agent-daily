"""输出抽象层：OutputProvider 接口 + 各实现。"""

from .base import IdempotencyRecord, OutputError, OutputProvider, OutputRegistry
from .feishu import FeishuProvider
from .feishu_cli import FeishuCLIProvider
from .local_file import LocalFileProvider
from .telegram import TelegramProvider

__all__ = [
    "OutputProvider",
    "OutputError",
    "OutputRegistry",
    "IdempotencyRecord",
    "LocalFileProvider",
    "FeishuProvider",
    "FeishuCLIProvider",
    "TelegramProvider",
]
