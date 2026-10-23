"""核心数据模型（不依赖 Qt）。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
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
    普通积木的 ``params`` 保存每个常驻输入框里的值。
    """

    kind: str
    text: str = ""
    params: dict[str, str] = field(default_factory=dict)
    children: list["Block"] = field(default_factory=list)
    else_children: list["Block"] = field(default_factory=list)
    expressions: dict[str, "Block"] = field(default_factory=dict)
    value_modes: dict[str, str] = field(default_factory=dict)
    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "text": self.text,
            "params": dict(self.params),
            "children": [child.to_dict() for child in self.children],
            "else_children": [child.to_dict() for child in self.else_children],
            "expressions": {
                name: child.to_dict() for name, child in self.expressions.items()
            },
            "value_modes": dict(self.value_modes),
            "x": self.x,
            "y": self.y,
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

        params_data = data.get("params", {})
        if not isinstance(params_data, dict):
            raise ValueError("block.params 必须是对象")
        params: dict[str, str] = {}
        for name, value in params_data.items():
            if not isinstance(name, str) or not isinstance(value, str):
                raise ValueError("block.params 的键和值必须是字符串")
            params[name] = value

        children_data = data.get("children", [])
        if not isinstance(children_data, list):
            raise ValueError("block.children 必须是数组")
        children = [cls.from_dict(child) for child in children_data]

        else_data = data.get("else_children", [])
        if not isinstance(else_data, list):
            raise ValueError("block.else_children 必须是数组")
        else_children = [cls.from_dict(child) for child in else_data]

        expressions_data = data.get("expressions", {})
        if not isinstance(expressions_data, dict):
            raise ValueError("block.expressions 必须是对象")
        expressions = {
            name: cls.from_dict(child)
            for name, child in expressions_data.items()
            if isinstance(name, str)
        }

        modes_data = data.get("value_modes", {})
        if not isinstance(modes_data, dict):
            raise ValueError("block.value_modes 必须是对象")
        value_modes = {
            name: str(mode)
            for name, mode in modes_data.items()
            if isinstance(name, str)
        }

        x = float(data.get("x", 0.0) or 0.0)
        y = float(data.get("y", 0.0) or 0.0)
        return cls(
            kind=kind,
            text=text,
            params=params,
            children=children,
            else_children=else_children,
            expressions=expressions,
            value_modes=value_modes,
            x=x,
            y=y,
        )


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
    name: str = ""
    path: Path | None = field(default=None, compare=False, repr=False)
    hidden: bool = field(default=False, compare=False, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "description": self.description,
            "script": self.script,
            "enabled": self.enabled,
            "blocks": [block.to_dict() for block in self.blocks],
        }
