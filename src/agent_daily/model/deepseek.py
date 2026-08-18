"""DeepSeekProvider —— 备用模型提供者。

调用 DeepSeek API（OpenAI 兼容 /chat/completions）。api_key 来自 secrets.env
的 ``DEEPSEEK_API_KEY``。未配置时初始化抛 ModelAPIError（由上层捕获，不影响
本地模型运行）。
"""

from __future__ import annotations

from typing import Any

import httpx

from ..config.schema import DeepSeekConfig
from .exceptions import ModelAPIError, ModelTimeoutError


class DeepSeekProvider:
    name = "deepseek"

    def __init__(
        self,
        config: DeepSeekConfig,
        api_key: str,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ModelAPIError("缺少 DEEPSEEK_API_KEY（请在 secrets.env 配置）")
        self.config = config
        self.api_key = api_key
        # client 可注入（测试用 MockTransport），默认按配置创建
        self._client = client or httpx.Client(
            base_url=config.base_url, timeout=config.timeout_seconds
        )

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        payload: dict[str, Any] = {"model": self.config.model, "messages": messages}
        if kwargs.get("max_tokens") is not None:
            payload["max_tokens"] = kwargs["max_tokens"]
        if kwargs.get("temperature") is not None:
            payload["temperature"] = kwargs["temperature"]

        try:
            resp = self._client.post(
                "/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        except httpx.TimeoutException as exc:
            raise ModelTimeoutError(f"DeepSeek 调用超时：{exc}") from exc
        except httpx.HTTPError as exc:
            raise ModelAPIError(f"DeepSeek 请求失败：{exc}") from exc

        if resp.status_code != 200:
            raise ModelAPIError(
                f"DeepSeek API 返回 {resp.status_code}：{resp.text[:200]}"
            )

        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelAPIError(f"DeepSeek 响应格式异常：{resp.text[:200]}") from exc
