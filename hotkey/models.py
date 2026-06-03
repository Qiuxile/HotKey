"""热键数据模型定义。"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class HotKeyEntry:
    """热键条目数据模型。"""
    key: str
    description: str = ""
    code: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HotKeyEntry':
        """从字典创建 HotKeyEntry。"""
        return cls(
            key=data.get('key', ''),
            description=data.get('description', ''),
            code=data.get('code', []),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）。"""
        return {
            'key': self.key,
            'description': self.description,
            'code': self.code,
        }


@dataclass
class DragState:
    """拖拽状态数据模型。"""
    item: int = -1
    text: str = ""
