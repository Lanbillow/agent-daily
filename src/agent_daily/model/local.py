"""LocalMLXProvider —— 默认模型提供者。

通过 subprocess 调用 mlxsvc CLI（``uv run mlxsvc run --prompt ...``），
**不 import mlx / mlx_lm，不直接加载模型权重，不管理模型生命周期**（加载与
释放由 mlxsvc 负责）。

messages 组装：
  - system 消息 → ``--system``
  - 其余消息按序拼接 → ``--prompt``

失败映射：
  - mlxsvc 目录缺失          → ModelLoadError
  - 命令无法启动 / 非零退出   → ModelProcessError
  - 超时                      → ModelTimeoutError
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ..config.schema import LocalModelConfig
from .exceptions import ModelLoadError, ModelProcessError, ModelTimeoutError


class LocalMLXProvider:
    name = "local"

    def __init__(self, config: LocalModelConfig, project_root: str | Path | None = None) -> None:
        self.config = config
        self._cwd = self._resolve_cwd(config.cwd, project_root)

    @staticmethod
    def _resolve_cwd(cwd: str, project_root: str | Path | None) -> Path:
        p = Path(cwd)
        if not p.is_absolute() and project_root is not None:
            p = Path(project_root) / p
        return p.resolve()

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if not self._cwd.exists():
            raise ModelLoadError(f"mlxsvc 目录不存在：{self._cwd}")

        system, prompt = self._assemble(messages)
        cmd = list(self.config.command) + ["run", "--prompt", prompt]
        if system:
            cmd += ["--system", system]
        if kwargs.get("max_tokens") is not None:
            cmd += ["--max-tokens", str(kwargs["max_tokens"])]
        if kwargs.get("temperature") is not None:
            cmd += ["--temperature", str(kwargs["temperature"])]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self._cwd),
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise ModelTimeoutError(
                f"mlxsvc 调用超时（{self.config.timeout_seconds}s）"
            ) from exc
        except FileNotFoundError as exc:
            raise ModelProcessError(
                f"命令未找到：{cmd[0]}（请确认 uv 在 PATH 中）"
            ) from exc
        except OSError as exc:
            raise ModelProcessError(f"mlxsvc 子进程启动失败：{exc}") from exc

        if proc.returncode != 0:
            raise ModelProcessError(
                f"mlxsvc 退出码 {proc.returncode}：{proc.stderr.strip()}"
            )
        return proc.stdout.strip()

    @staticmethod
    def _assemble(messages: list[dict[str, str]]) -> tuple[str | None, str]:
        system_parts = [
            str(m.get("content", "")) for m in messages if m.get("role") == "system"
        ]
        system = "\n\n".join(p for p in system_parts if p) or None

        user_parts = [
            str(m.get("content", "")) for m in messages if m.get("role") != "system"
        ]
        prompt = "\n\n".join(p for p in user_parts if p)
        return system, prompt
