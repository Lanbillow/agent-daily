"""模型层异常体系。

上层（Agent / Jobs）只需捕获 ``ModelError`` 基类即可统一处理模型失败；
需要精细区分时再捕获具体子类。
"""

from __future__ import annotations


class ModelError(Exception):
    """模型层错误基类。"""


class ModelLoadError(ModelError):
    """本地模型基础设施缺失/加载失败（如 mlxsvc 目录不存在）。"""


class ModelTimeoutError(ModelError):
    """模型调用超时。"""


class ModelProcessError(ModelError):
    """子进程/命令执行失败（启动失败或非零退出）。"""


class ModelAPIError(ModelError):
    """远端 API 调用失败（HTTP 错误 / 响应异常 / 缺密钥）。"""
