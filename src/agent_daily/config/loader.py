"""配置与密钥加载。

约定路径（相对项目根）：
  config/config.yaml        实际配置（可缺失，缺失时使用 schema 默认值）
  config/config.yaml.example 模板（仅作参照）
  config/secrets.env        密钥（可缺失，缺失时返回空 dict）

不依赖第三方配置库之外的能力；secrets.env 用内置解析器读取（KEY=VALUE）。
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml

from .schema import Settings

# 项目根 = 本文件向上 3 级：.../agent-daily/src/agent_daily/config/loader.py
PROJECT_ROOT = Path(__file__).resolve().parents[3]

CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
CONFIG_EXAMPLE_FILE = CONFIG_DIR / "config.yaml.example"
SECRETS_FILE = CONFIG_DIR / "secrets.env"

# 顶层标量字段（非 section）
_SCALAR_FIELDS = ("timezone",)
# 嵌套 section 字段（各自是 dataclass）
_SECTION_FIELDS = ("model", "github", "output", "storage", "logging")


def _merge(target: Any, source: dict) -> None:
    """把 source 递归合并进 dataclass target，忽略未知字段。"""
    known = {f.name for f in fields(target)}
    for key, value in source.items():
        if key not in known:
            continue
        current = getattr(target, key)
        if isinstance(value, dict) and is_dataclass(current):
            _merge(current, value)
        else:
            setattr(target, key, value)


def load_config(path: Path | str | None = None) -> Settings:
    """加载配置；缺失文件或非法 YAML 时回退到默认值（不抛异常）。"""
    settings = Settings()
    p = Path(path) if path is not None else CONFIG_FILE
    if not p.exists():
        return settings

    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return settings
    if not isinstance(data, dict):
        return settings

    for scalar in _SCALAR_FIELDS:
        if scalar in data:
            setattr(settings, scalar, data[scalar])
    for section in _SECTION_FIELDS:
        if section in data and isinstance(data[section], dict):
            _merge(getattr(settings, section), data[section])
    return settings


def load_secrets(path: Path | str | None = None) -> dict[str, str]:
    """解析 secrets.env（KEY=VALUE），缺失时返回空 dict。"""
    p = Path(path) if path is not None else SECRETS_FILE
    if not p.exists():
        return {}
    secrets: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        secrets[key.strip()] = value.strip().strip("\"'")
    return secrets


def mlxsvc_dir(settings: Settings | None = None) -> Path:
    """解析 mlxsvc 项目目录（来自 model.local.cwd，相对项目根）。"""
    cfg = settings or load_config()
    cwd = cfg.model.local.cwd or "../mlx-service"
    return (PROJECT_ROOT / cwd).resolve()
