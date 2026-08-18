"""FeishuProvider —— 飞书开放 API 输出。

流程：
  1. 获取 tenant_access_token（app_id + app_secret）
  2. 创建文档（docx）
  3. 写入内容块（段落 → 文本块）
  4. 返回 document_id

密钥来自 secrets.env（FEISHU_APP_ID / FEISHU_APP_SECRET），禁止硬编码。
失败抛 OutputError，禁止空成功。

幂等：record_path 配置后，相同 key（默认 title）重复执行只创建一次文档，
返回已记录的 document_id。
"""

from __future__ import annotations

from typing import Any

import httpx

from .base import IdempotencyRecord, OutputError

FEISHU_BASE_URL = "https://open.feishu.cn"

# 段落 → 文本块
_BLOCK_TEXT = 2


class FeishuProvider:
    name = "feishu"

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        folder_token: str = "",
        base_url: str = FEISHU_BASE_URL,
        record_path: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        if not app_id or not app_secret:
            raise OutputError(
                "缺少 FEISHU_APP_ID / FEISHU_APP_SECRET（请在 secrets.env 配置）"
            )
        self.app_id = app_id
        self.app_secret = app_secret
        self.folder_token = folder_token
        self._client = client or httpx.Client(base_url=base_url, timeout=30.0)
        self._records = IdempotencyRecord(record_path) if record_path else None

    # -- 对外 -----------------------------------------------------------
    def write(self, title: str, content: str, **kwargs: Any) -> str:
        key = str(kwargs.get("key") or title)

        if self._records is not None:
            existing = self._records.get(key)
            if existing:
                return existing  # 幂等：已有记录，直接返回，不重复创建

        token = self._get_token()
        document_id = self._create_document(title, token)
        self._write_blocks(document_id, content, token)

        if self._records is not None:
            self._records.set(key, document_id)
        return document_id

    # -- 飞书 Open API 各步 --------------------------------------------
    def _get_token(self) -> str:
        data = self._post(
            "/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
        )
        token = data.get("tenant_access_token")
        if not token:
            raise OutputError(f"获取 tenant_access_token 失败：{data}")
        return token

    def _create_document(self, title: str, token: str) -> str:
        body: dict[str, Any] = {"title": title}
        if self.folder_token:
            body["folder_token"] = self.folder_token
        data = self._post("/open-apis/docx/v1/documents", json=body, token=token)
        document_id = data.get("data", {}).get("document", {}).get("document_id")
        if not document_id:
            raise OutputError(f"创建文档失败：{data}")
        return document_id

    def _write_blocks(self, document_id: str, content: str, token: str) -> None:
        paragraphs = [p for p in content.splitlines() if p.strip()] or [content]
        children = [
            {
                "block_type": _BLOCK_TEXT,
                "text": {"elements": [{"text_run": {"content": p}}]},
            }
            for p in paragraphs
        ]
        self._post(
            f"/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children",
            json={"children": children},
            token=token,
        )

    # -- 统一 HTTP 封装 -------------------------------------------------
    def _post(self, path: str, json: dict, token: str | None = None) -> dict:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            resp = self._client.post(path, json=json, headers=headers)
        except httpx.HTTPError as exc:
            raise OutputError(f"飞书 API 请求失败：{exc}") from exc

        if resp.status_code != 200:
            raise OutputError(f"飞书 API 返回 HTTP {resp.status_code}：{resp.text[:200]}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise OutputError(f"飞书 API 响应非 JSON：{resp.text[:200]}") from exc

        if data.get("code") != 0:
            raise OutputError(f"飞书 API 错误 code={data.get('code')} msg={data.get('msg')}")
        return data
