"""SVG 图标加载：把黑色线性图标染成当前深色主题的文字色。"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap


def assets_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parents[2] / "assets"


def asset_path(name: str) -> Path:
    return assets_dir() / name


def colored_icon(name: str) -> QIcon:
    path = asset_path(name)
    return QIcon(str(path)) if path.exists() else QIcon()


def themed_icon(name: str, color: str = "#E5E5F7", size: int = 24) -> QIcon:
    """加载黑色 SVG 并整体染成指定颜色；找不到文件时返回空图标。"""
    path = asset_path(name)
    if not path.exists():
        return QIcon()
    icon = QIcon(str(path))
    pixmap = icon.pixmap(QSize(size, size))
    if pixmap.isNull():
        return icon
    pixmap = pixmap.copy()
    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    return QIcon(pixmap)
