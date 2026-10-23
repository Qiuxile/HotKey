"""无边框窗口的自定义标题栏（菜单并入同一行）。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QAction, QFontMetrics
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QStyle,
    QToolButton,
    QWidget,
)

from hotkey.ui.icons import themed_icon

TITLE_MAX_WIDTH = 300


class TitleBar(QFrame):
    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self.setObjectName("titleBar")
        self.setFixedHeight(40)
        self._window = window
        self._full_title = "HotKey"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(4)

        self.title_label = QLabel("HotKey", self)
        self.title_label.setObjectName("titleText")
        self.title_label.setMaximumWidth(TITLE_MAX_WIDTH)
        self.title_label.setMinimumWidth(0)
        self.title_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.title_label)

        self._menu_row = QHBoxLayout()
        self._menu_row.setContentsMargins(0, 0, 0, 0)
        self._menu_row.setSpacing(2)
        layout.addLayout(self._menu_row)
        layout.addStretch(1)

        self.menu_buttons: list[QToolButton] = []
        self.menus: list[QMenu] = []

        self.min_button = self._make_button(
            QStyle.StandardPixmap.SP_TitleBarMinButton, "最小化"
        )
        self.min_button.clicked.connect(self._window.showMinimized)
        layout.addWidget(self.min_button)

        self.max_button = self._make_button(
            QStyle.StandardPixmap.SP_TitleBarMaxButton, "最大化"
        )
        self.max_button.clicked.connect(self._toggle_maximized)
        layout.addWidget(self.max_button)

        self.close_button = QToolButton(self)
        self.close_button.setObjectName("titleClose")
        self.close_button.setIcon(themed_icon("close.svg"))
        self.close_button.setIconSize(QSize(14, 14))
        self.close_button.setFixedSize(32, 28)
        self.close_button.setToolTip("关闭")
        self.close_button.setAutoRaise(True)
        self.close_button.clicked.connect(self._window.close)
        layout.addWidget(self.close_button)

        self._manual_drag = False
        self._drag_offset = QPoint()

    def _make_button(
        self,
        icon: QStyle.StandardPixmap,
        tooltip: str,
    ) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName("titleButton")
        button.setIcon(self.style().standardIcon(icon))
        button.setIconSize(QSize(14, 14))
        button.setFixedSize(32, 28)
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        return button

    # ---------------------------------------------------------------- 菜单

    def attach_menus(
        self, menus: list[tuple[str, list[QAction]]]
    ) -> None:
        for title, actions in menus:
            button = QToolButton(self)
            button.setObjectName("titleMenuButton")
            button.setText(title)
            button.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextOnly
            )
            button.setFixedHeight(28)
            button.setAutoRaise(True)
            self._menu_row.addWidget(button)

            menu = QMenu(button)
            menu.addActions(actions)
            menu.hide()
            button.clicked.connect(
                lambda _checked=False, m=menu, b=button: self._popup(m, b)
            )
            self.menu_buttons.append(button)
            self.menus.append(menu)

    def _popup(self, menu: QMenu, button: QToolButton) -> None:
        if menu.isVisible():
            menu.hide()
            return
        menu.popup(button.mapToGlobal(QPoint(0, button.height())))

    # ---------------------------------------------------------------- 状态

    def set_title(self, text: str) -> None:
        self._full_title = text
        self.title_label.setToolTip(text)
        self._apply_title()

    def _apply_title(self) -> None:
        # 右侧固定控件大约占 300px，窄窗口优先保证菜单按钮可见
        bar_width = self.width()
        if bar_width < 200:
            bar_width = self._window.width()
        available = max(0, min(TITLE_MAX_WIDTH, bar_width - 300))
        if available < 24:
            self.title_label.setText("")
            return
        metrics = QFontMetrics(self.title_label.font())
        self.title_label.setText(
            metrics.elidedText(
                self._full_title, Qt.TextElideMode.ElideRight, available
            )
        )

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._apply_title()
        super().resizeEvent(event)

    def set_maximized(self, maximized: bool) -> None:
        icon = (
            QStyle.StandardPixmap.SP_TitleBarNormalButton
            if maximized
            else QStyle.StandardPixmap.SP_TitleBarMaxButton
        )
        self.max_button.setIcon(self.style().standardIcon(icon))
        self.max_button.setToolTip("还原" if maximized else "最大化")

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
