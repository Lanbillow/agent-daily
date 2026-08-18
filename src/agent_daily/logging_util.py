"""日志配置：stderr + 轮转文件（供 CLI / 长期运行使用）。"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

_configured = False


def setup_logging(level: str = "INFO", log_dir: str | Path = "data/logs") -> logging.Logger:
    global _configured
    logger = logging.getLogger("agent_daily")

    if _configured:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    try:
        p = Path(log_dir)
        p.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            p / "agent-daily.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError as exc:  # pragma: no cover
        logger.warning("无法创建日志文件：%s", exc)

    logger.propagate = False
    _configured = True
    return logger
