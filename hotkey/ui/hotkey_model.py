"""热键列表模型与搜索代理。"""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtGui import QColor

from hotkey.core import keymap
from hotkey.core.models import HotKey

HEADERS = ("名称", "热键", "状态")


class HotKeyTableModel(QAbstractTableModel):
    def __init__(self, entries: list[HotKey] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._entries: list[HotKey] = list(entries or [])

    # ---------------------------------------------------------------- 基本接口

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._entries)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(HEADERS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        entry = self._entries[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return entry.name or entry.description or "未命名"
            if column == 1:
                return keymap.keyboard_to_qt(entry.key) if entry.key else "—"
            if column == 2:
                return "启用" if entry.enabled else "停用"
        elif role == Qt.ItemDataRole.ToolTipRole:
            if column == 0:
                return entry.description or (str(entry.path) if entry.path else "（无描述）")
            if column == 1:
                return entry.key or "未设置热键，可手动运行或导出"
        elif role == Qt.ItemDataRole.TextAlignmentRole and column == 1:
            return Qt.AlignmentFlag.AlignCenter
        elif role == Qt.ItemDataRole.TextAlignmentRole and column == 2:
            return Qt.AlignmentFlag.AlignCenter
        elif role == Qt.ItemDataRole.ForegroundRole and column == 2:
            return None if entry.enabled else QColor("#9aa5b1")
        elif role == Qt.ItemDataRole.UserRole:
            return entry.id
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return HEADERS[section]
        return section + 1

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    # ---------------------------------------------------------------- 数据操作

    def entries(self) -> list[HotKey]:
        return list(self._entries)

    def set_entries(self, entries: list[HotKey]) -> None:
        self.beginResetModel()
        self._entries = list(entries)
        self.endResetModel()

    def entry(self, row: int) -> HotKey:
        return self._entries[row]

    def row_of(self, hotkey_id: str) -> int | None:
        for row, entry in enumerate(self._entries):
            if entry.id == hotkey_id:
                return row
        return None

    def add(self, entry: HotKey) -> int:
        row = len(self._entries)
        self.beginInsertRows(QModelIndex(), row, row)
        self._entries.append(entry)
        self.endInsertRows()
        return row

    def remove(self, row: int) -> None:
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._entries[row]
        self.endRemoveRows()

    def toggle(self, row: int) -> None:
        entry = self._entries[row]
        entry.enabled = not entry.enabled
        self.touch(row)

    def touch(self, row: int) -> None:
        left = self.index(row, 0)
        right = self.index(row, len(HEADERS) - 1)
        self.dataChanged.emit(left, right)


class HotKeyFilterProxy(QSortFilterProxyModel):
    """按热键和描述过滤；选中项通过 mapToSource 回到源模型。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._needle = ""
        self.setDynamicSortFilter(True)

    def set_search_text(self, text: str) -> None:
        needle = text.strip().lower()
        if needle == self._needle:
            return
        self.beginFilterChange()
        self._needle = needle
        self.endFilterChange()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._needle:
            return True
        model = self.sourceModel()
        if model is None:
            return True
        entry = model.entry(source_row)
        haystack = (
            f"{entry.name} {entry.key} {entry.description}".lower()
        )
        return self._needle in haystack
