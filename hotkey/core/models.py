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
class Block:
    """右侧积木栏里的一块。

    ``kind`` 是 ``catalog.Snippet.id``；空白积木用 ``"empty"``，
    此时 ``text`` 就是用户自己写的 Python 代码。
    """

    kind: str
    text: str = ""
    children: list["Block"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "text": self.text,
            "children": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Block":
        if not isinstance(data, dict):
            raise ValueError("block 必须是对象")
        kind = data.get("kind")
        text = data.get("text", "")
        if not isinstance(kind, str) or not kind:
            raise ValueError("block.kind 无效")
        if not isinstance(text, str):
            raise ValueError("block.text 无效")

        children_data = data.get("children", [])
        if not isinstance(children_data, list):
            raise ValueError("block.children 必须是数组")
        children = [cls.from_dict(child) for child in children_data]
        return cls(kind=kind, text=text, children=children)


@dataclass
class HotKey:
    """一条热键配置。

    ``blocks`` 是右侧的积木结构，``script`` 是由积木生成的整段脚本文本。
    ``script`` 保留是为了执行、兼容旧配置和导出；界面以 ``blocks`` 为准。
    """

    key: str
    description: str = ""
    script: str = ""
    enabled: bool = True
    id: str = field(default_factory=new_id)
    blocks: list[Block] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "description": self.description,
            "script": self.script,
            "enabled": self.enabled,
            "blocks": [block.to_dict() for block in self.blocks],
        }
