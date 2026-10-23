"""应用图标（编辑器与监听器共用）。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from hotkey.ui.icons import asset_path


def app_icon() -> QIcon:
    """优先使用 assets/hotkey.ico（Windows 多尺寸），缺失时回退 PNG/内置图标。"""
    for name in ("hotkey.ico", "hotkey.png"):
        path = asset_path(name)
        if path.exists():
            return QIcon(str(path))

    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#151628"))
    painter.drawRoundedRect(2, 2, 60, 60, 14, 14)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#7F7FD5"), 3))
    painter.drawRoundedRect(5, 5, 54, 54, 11, 11)

    pen = QPen(QColor("#E5E5F7"), 5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawLine(18, 21, 30, 31)
    painter.drawLine(30, 31, 18, 41)
    painter.drawLine(35, 43, 47, 43)
    painter.end()
    return QIcon(pixmap)
