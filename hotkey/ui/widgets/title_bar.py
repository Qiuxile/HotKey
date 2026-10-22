"""无边框窗口的自定义标题栏。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QWidget


class TitleBar(QFrame):
    theme_clicked = Signal()

    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self.setObjectName("titleBar")
        self.setFixedHeight(40)
        self._window = window

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 8, 0)
        layout.setSpacing(6)

        icon = QLabel("HK", self)
        icon.setObjectName("titleIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        self.title_label = QLabel("HotKey", self)
        self.title_label.setObjectName("titleText")
        layout.addWidget(self.title_label)
        layout.addStretch(1)

        self.theme_button = QToolButton(self)
        self.theme_button.setObjectName("titleButton")
        self.theme_button.setToolTip("切换深色 / 浅色主题")
        self.theme_button.clicked.connect(self.theme_clicked.emit)
        layout.addWidget(self.theme_button)

        self.min_button = QToolButton(self)
        self.min_button.setObjectName("titleButton")
        self.min_button.setText("—")
        self.min_button.setToolTip("最小化")
        self.min_button.clicked.connect(self._window.showMinimized)
        layout.addWidget(self.min_button)

        self.max_button = QToolButton(self)
        self.max_button.setObjectName("titleButton")
        self.max_button.setText("□")
        self.max_button.setToolTip("最大化 / 还原")
        self.max_button.clicked.connect(self._toggle_maximized)
        layout.addWidget(self.max_button)

        self.close_button = QToolButton(self)
        self.close_button.setObjectName("titleClose")
        self.close_button.setText("✕")
        self.close_button.setToolTip("关闭")
        self.close_button.clicked.connect(self._window.close)
        layout.addWidget(self.close_button)

        self._manual_drag = False
        self._drag_offset = QPoint()

    # ---------------------------------------------------------------- 状态

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)

    def set_maximized(self, maximized: bool) -> None:
        self.max_button.setText("❐" if maximized else "□")

    def set_theme_dark(self, dark: bool) -> None:
        self.theme_button.setText("☀" if dark else "🌙")
        self.theme_button.setToolTip(
            "切换浅色主题" if dark else "切换深色主题"
        )

    # ---------------------------------------------------------------- 拖动

    def _toggle_maximized(self) -> None:
        window = self._window
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()
        self.set_maximized(window.isMaximized())

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        handle = self._window.windowHandle()
        if handle is not None and handle.startSystemMove():
            self._manual_drag = False
            event.accept()
            return

        self._manual_drag = True
        self._drag_offset = (
            event.globalPosition().toPoint()
            - self._window.frameGeometry().topLeft()
        )
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._manual_drag and event.buttons() & Qt.MouseButton.LeftButton:
            self._window.move(
                event.globalPosition().toPoint() - self._drag_offset
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._manual_drag = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
