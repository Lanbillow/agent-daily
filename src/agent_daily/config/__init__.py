"""配置模块：结构定义 + 加载 + 密钥。"""

from .loader import (
    CONFIG_DIR,
    CONFIG_EXAMPLE_FILE,
    CONFIG_FILE,
    PROJECT_ROOT,
    SECRETS_FILE,
    load_config,
    load_secrets,
    mlxsvc_dir,
)
from .schema import Settings

__all__ = [
    "Settings",
    "PROJECT_ROOT",
    "CONFIG_DIR",
    "CONFIG_FILE",
    "CONFIG_EXAMPLE_FILE",
    "SECRETS_FILE",
    "load_config",
    "load_secrets",
    "mlxsvc_dir",
]
