"""Control Plane（管理/观察层，Phase 1.5）。

只读后端（S1-A）：FastAPI 提供对 v0.1.0 共享数据文件的只读访问。
不执行 workflow，不 import 执行模块。
"""

from .api import app, create_app
from .repo import Repo

__all__ = ["Repo", "create_app", "app"]
