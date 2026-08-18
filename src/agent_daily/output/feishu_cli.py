"""FeishuCLIProvider —— 通过 lark-cli 创建飞书 Markdown 文档。

个人使用场景：lark-cli 已完成 OAuth 登录，`markdown +create` 可直接把 Markdown
内容（stdin）创建为飞书文档，无需 app_id / app_secret。

命令：
  echo(content) | lark-cli markdown +create --content - --name "<title>.md"

失败一律抛 OutputError（禁止假成功）：
  - lark-cli 不存在 / 启动失败
  - 子进程返回非 0
  - 超时
  - stdout 无有效结果（非 JSON / ok != true / 缺 file_token）
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from .base import OutputError


class FeishuCLIProvider:
    name = "feishu_cli"

    def __init__(self, command: str = "lark-cli", timeout_seconds: int = 120) -> None:
        self.command = command
        self.timeout_seconds = timeout_seconds

    def write(self, title: str, content: str, **kwargs: Any) -> str:
        name = f"{title}.md"
        cmd = [self.command, "markdown", "+create", "--name", name, "--content", "-"]

        try:
            proc = subprocess.run(
                cmd,
                input=content,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise OutputError(
                f"未找到命令：{self.command}（请确认 lark-cli 已安装并在 PATH 中）"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise OutputError(f"lark-cli 调用超时（{self.timeout_seconds}s）") from exc
        except OSError as exc:
            raise OutputError(f"lark-cli 启动失败：{exc}") from exc

        if proc.returncode != 0:
            raise OutputError(f"lark-cli 退出码 {proc.returncode}：{proc.stderr.strip()}")

        return self._parse_result(proc.stdout)

    @staticmethod
    def _parse_result(stdout: str) -> str:
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise OutputError(f"lark-cli 无有效结果（stdout 非 JSON）：{stdout[:200]!r}") from exc

        # 成功契约：ok == true（非 code == 0）
        if data.get("ok") is not True:
            err = data.get("error") or data.get("msg") or data
            raise OutputError(f"lark-cli 返回失败：{err}")

        file_token = (data.get("data") or {}).get("file_token")
        if not file_token:
            raise OutputError(f"lark-cli 无有效结果（缺 file_token）：{data}")
        return str(file_token)
