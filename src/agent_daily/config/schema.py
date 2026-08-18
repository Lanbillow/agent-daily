"""配置结构定义（dataclass）。

字段名与 config/config.yaml.example 一一对应。默认值即「未提供 config.yaml
时的兜底配置」，确保系统在任何情况下都能以最小可用形态启动。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LocalModelConfig:
    """本地 MLX 模型（通过 mlxsvc subprocess 调用）。"""

    mode: str = "subprocess"
    command: list[str] = field(default_factory=lambda: ["uv", "run", "mlxsvc"])
    cwd: str = "../mlx-service"
    timeout_seconds: int = 900


@dataclass
class DeepSeekConfig:
    """DeepSeek 远端模型。"""

    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    timeout_seconds: int = 120


@dataclass
class ModelConfig:
    primary: str = "local"
    fallback: str = "deepseek"
    local: LocalModelConfig = field(default_factory=LocalModelConfig)
    deepseek: DeepSeekConfig = field(default_factory=DeepSeekConfig)


@dataclass
class GithubSourceConfig:
    """GitHub 数据源切换点。"""

    provider: str = "mirror"  # official | mirror


@dataclass
class GithubConfig:
    source: GithubSourceConfig = field(default_factory=GithubSourceConfig)
    # provider 名 -> {base_url, trending_path, format, ...}（原始 dict，由 SourceAdapter 解释）
    providers: dict = field(default_factory=dict)
    timeout_seconds: float = 30.0


@dataclass
class LocalFileOutputConfig:
    enabled: bool = True
    dir: str = "data/output"


@dataclass
class FeishuOutputConfig:
    enabled: bool = False
    folder_token: str = ""


@dataclass
class FeishuCLIOutputConfig:
    command: str = "lark-cli"
    timeout_seconds: int = 120


@dataclass
class OutputConfig:
    default: str = "local_file"
    local_file: LocalFileOutputConfig = field(default_factory=LocalFileOutputConfig)
    feishu: FeishuOutputConfig = field(default_factory=FeishuOutputConfig)
    feishu_cli: FeishuCLIOutputConfig = field(default_factory=FeishuCLIOutputConfig)


@dataclass
class StorageConfig:
    data_dir: str = "data"
    processed_dir: str = "data/processed"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    dir: str = "data/logs"


@dataclass
class Settings:
    timezone: str = "Asia/Shanghai"
    model: ModelConfig = field(default_factory=ModelConfig)
    github: GithubConfig = field(default_factory=GithubConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
