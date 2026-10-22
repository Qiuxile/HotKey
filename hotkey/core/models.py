"""核心数据模型（不依赖 Qt）。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IssueLevel(str, Enum):
    """校验结果级别。"""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Issue:
    """一条校验问题。"""

    level: IssueLevel
    message: str
    line: int | None = None

    def __str__(self) -> str:
        prefix = f"第{self.line}行: " if self.line else ""
        return f"{prefix}{self.message}"


def new_id() -> str:
    """生成热键条目的稳定标识。"""
    return uuid.uuid4().hex


@dataclass
class HotKey:
    """一条热键配置。

    ``script`` 是整段脚本（不再是按行拆分的列表），这样 ``for`` / ``if``
    这类多行结构才能被正确编译和执行。
    """

    key: str
    description: str = ""
    script: str = ""
    enabled: bool = True
    id: str = field(default_factory=new_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "description": self.description,
            "script": self.script,
            "enabled": self.enabled,
        }
