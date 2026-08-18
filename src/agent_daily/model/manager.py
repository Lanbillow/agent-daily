"""ModelManager —— 仅实现 failover，不做智能路由。

逻辑固定：
  chat() → try primary（默认 LocalMLXProvider）
           except ModelError → try fallback（默认 DeepSeekProvider）
           两者都失败 → 抛 ModelError

不做任务复杂度判断、不做自动模型选择。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from ..config.schema import Settings
from .base import ModelProvider
from .deepseek import DeepSeekProvider
from .exceptions import ModelError
from .local import LocalMLXProvider

log = logging.getLogger("agent_daily.model")


class ModelManager:
    def __init__(self, primary: ModelProvider, fallback: ModelProvider | None = None) -> None:
        self.primary = primary
        self.fallback = fallback

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        try:
            return self._invoke(self.primary, messages, **kwargs)
        except ModelError as primary_err:
            log.warning("primary 模型失败，尝试 fallback：%s", primary_err)
            return self._fallback_or_raise(messages, primary_err, **kwargs)

    def _fallback_or_raise(
        self, messages: list[dict[str, str]], primary_err: ModelError, **kwargs: Any
    ) -> str:
        if self.fallback is None:
            raise primary_err
        try:
            return self._invoke(self.fallback, messages, **kwargs)
        except ModelError as fallback_err:
            raise ModelError(
                f"主模型与备用模型均失败：primary={primary_err}; fallback={fallback_err}"
            ) from fallback_err

    def _invoke(self, provider: ModelProvider, messages: list[dict[str, str]], **kwargs: Any) -> str:
        start = time.perf_counter()
        try:
            result = provider.chat(messages, **kwargs)
            duration = time.perf_counter() - start
            log.info(
                "model_call provider=%s success=true duration=%.3fs",
                provider.name, duration,
            )
            return result
        except Exception as exc:
            duration = time.perf_counter() - start
            log.warning(
                "model_call provider=%s success=false duration=%.3fs error=%s",
                provider.name, duration, exc,
            )
            raise


def create_model_manager(
    settings: Settings,
    secrets: dict[str, str],
    project_root: Any = None,
) -> ModelManager:
    """装配 ModelManager（primary=local，fallback=deepseek）。

    DeepSeek 未配置时初始化失败（ModelAPIError），此处捕获并置 fallback=None，
    保证本地模型始终可用。
    """
    if project_root is None:
        from ..config.loader import PROJECT_ROOT

        project_root = PROJECT_ROOT

    local = LocalMLXProvider(settings.model.local, project_root=project_root)

    deepseek: ModelProvider | None = None
    try:
        deepseek = DeepSeekProvider(
            settings.model.deepseek, secrets.get("DEEPSEEK_API_KEY", "")
        )
    except ModelError as exc:
        log.warning("DeepSeek 未配置或初始化失败，仅使用本地模型：%s", exc)

    return ModelManager(local, deepseek)
