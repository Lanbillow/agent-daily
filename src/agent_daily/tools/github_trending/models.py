"""GitHub 热门项目数据模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Repo:
    """一条热门项目（标准化结构，与数据源/格式无关）。"""

    name: str
    description: str
    language: str
    stars: int
    url: str
