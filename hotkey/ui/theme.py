"""深色主题：调色板、QSS 模板与配置。"""

from __future__ import annotations

import sys
from pathlib import Path
from string import Template

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from hotkey.core import storage

SETTINGS_ORG = "HotKey"
SETTINGS_APP = "HotKey"

PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0B0C15",
        "surface": "#151628",
        "surface_alt": "#1B1C33",
        "surface_high": "#2D2B55",
        "border": "#2D2B55",
        "text": "#E5E5F7",
        "muted": "#A6A6C9",
        "accent": "#7F7FD5",
        "accent_hover": "#9A9AEA",
        "input_bg": "#0F1020",
        "selection": "#2D2B55",
        "danger": "#FF6B81",
        "shadow": "#00000060",
    },
}


def _qss_path() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "hotkey" / "ui" / "theme.qss"
    return Path(__file__).resolve().parent / "theme.qss"


def theme_names() -> tuple[str, ...]:
    return ("dark",)


def settings() -> QSettings:
    # 放在配置目录而不是注册表，受限环境/便携模式都能用
    return QSettings(
        str(storage.config_root() / "settings.ini"),
        QSettings.Format.IniFormat,
    )


def current_theme() -> str:
    return "dark"


def render_qss(name: str = "dark") -> str:
    template = Template(_qss_path().read_text(encoding="utf-8"))
    return template.safe_substitute(PALETTES["dark"])


def build_palette(name: str = "dark") -> QPalette:
    colors = PALETTES["dark"]
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(colors["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors["input_bg"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["surface_alt"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors["surface"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["surface"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(colors["muted"]))
    palette.setColor(QPalette.ColorRole.Link, QColor(colors["accent"]))
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        QColor(colors["muted"]),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        QColor(colors["muted"]),
    )
    return palette


def apply_theme(app: QApplication, name: str = "dark") -> None:
    app.setPalette(build_palette("dark"))
    app.setStyleSheet(render_qss("dark"))
