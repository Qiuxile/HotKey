"""关于对话框：版本、作者、仓库、协议等应用信息。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from hotkey import __version__
from hotkey.ui.icon import app_icon

AUTHOR = "Surile"
REPOSITORY = "http://www.github.com/qiuxile/hotkey"
LICENSE_NAME = "MIT"
COPYRIGHT = "Copyright © 2026 Surile"


class AboutDialog(QDialog):
    """应用信息弹窗，内容保持本地、可复制、可打开仓库。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("aboutDialog")
        self.setWindowTitle("关于 HotKey")
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumWidth(480)
        self._copy_timer: QTimer | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(14)

        icon = QLabel(self)
        icon.setObjectName("aboutIcon")
        icon.setFixedSize(56, 56)
        icon.setPixmap(app_icon().pixmap(56, 56))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(icon)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("HotKey", self)
        title.setObjectName("aboutTitle")
        subtitle = QLabel("可视化热键自动化工具", self)
        subtitle.setObjectName("aboutSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        titles.addStretch(1)
        header.addLayout(titles, 1)
        layout.addLayout(header)

        separator = QFrame(self)
        separator.setObjectName("aboutSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        layout.addWidget(separator)

        form = QFormLayout()
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.version_label = self._value(__version__)
        self.author_label = self._value(AUTHOR)
        self.license_label = self._value(LICENSE_NAME)
        self.repo_label = QLabel(self)
        self.repo_label.setObjectName("aboutValue")
        self.repo_label.setOpenExternalLinks(True)
        self.repo_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.repo_label.setText(
            f'<a href="{REPOSITORY}">{REPOSITORY}</a>'
        )

        form.addRow(self._key("版本"), self.version_label)
        form.addRow(self._key("作者"), self.author_label)
        form.addRow(self._key("仓库"), self.repo_label)
        form.addRow(self._key("开源协议"), self.license_label)
        form.addRow(
            self._key("技术栈"),
            self._value("Python 3 · PySide6 · pyautogui"),
        )
        layout.addLayout(form)

        note = QLabel(
            "所有脚本只保存在本机 hks/ 目录，不会上传云端。\n"
            "使用中遇到问题，欢迎到仓库提交 Issue。",
            self,
        )
        note.setObjectName("aboutNote")
        note.setWordWrap(True)
        layout.addWidget(note)

        copyright_label = QLabel(COPYRIGHT, self)
        copyright_label.setObjectName("aboutCopyright")
        layout.addWidget(copyright_label)

        layout.addSpacing(2)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.open_repo_button = QPushButton("打开仓库", self)
        self.open_repo_button.setObjectName("aboutOpenRepo")
        self.open_repo_button.clicked.connect(self._open_repository)
        self.copy_button = QPushButton("复制信息", self)
        self.copy_button.setObjectName("aboutCopy")
        self.copy_button.clicked.connect(self._copy_info)
        buttons.addWidget(self.open_repo_button)
        buttons.addWidget(self.copy_button)
        buttons.addStretch(1)

        close_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self
        )
        close_buttons.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
        close_buttons.rejected.connect(self.reject)
        buttons.addWidget(close_buttons)
        layout.addLayout(buttons)

    def _key(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setObjectName("aboutKey")
        return label

    def _value(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setObjectName("aboutValue")
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        return label

    def _open_repository(self) -> None:
        QDesktopServices.openUrl(QUrl(REPOSITORY))

    def _copy_info(self) -> None:
        QGuiApplication.clipboard().setText(
            "\n".join(
                [
                    f"HotKey {__version__}",
                    f"作者：{AUTHOR}",
                    f"仓库：{REPOSITORY}",
                    f"开源协议：{LICENSE_NAME}",
                ]
            )
        )
        self.copy_button.setText("已复制")
        self._copy_timer = QTimer(self)
        self._copy_timer.setSingleShot(True)
        self._copy_timer.timeout.connect(lambda: self.copy_button.setText("复制信息"))
        self._copy_timer.start(1200)
