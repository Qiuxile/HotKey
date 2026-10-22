"""无边框窗口的四边/四角拖拽缩放。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PySide6.QtWidgets import QApplication, QWidget

BORDER = 6


class FramelessResizer(QObject):
    """在无边框窗口边缘按下鼠标时手动调整窗口 geometry。

    独立成类，避免主窗口里混入大量鼠标坐标/命中判断代码。
    """

    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self._window = window
        self._edges = Qt.Edge(0)
        self._origin = QPoint()
        self._start_geometry = QRect()

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    # ---------------------------------------------------------------- 命中

    def edges_at(self, pos: QPoint) -> Qt.Edge:
        if self._window.isMaximized() or self._window.isFullScreen():
            return Qt.Edge(0)

        edges = Qt.Edge(0)
        if pos.x() < BORDER:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() >= self._window.width() - BORDER:
            edges |= Qt.Edge.RightEdge
        if pos.y() < BORDER:
            edges |= Qt.Edge.TopEdge
        elif pos.y() >= self._window.height() - BORDER:
            edges |= Qt.Edge.BottomEdge
        return edges

    @staticmethod
    def cursor_for_edges(edges: Qt.Edge) -> Qt.CursorShape:
        left = bool(edges & Qt.Edge.LeftEdge)
        right = bool(edges & Qt.Edge.RightEdge)
        top = bool(edges & Qt.Edge.TopEdge)
        bottom = bool(edges & Qt.Edge.BottomEdge)
        if (left and top) or (right and bottom):
            return Qt.CursorShape.SizeFDiagCursor
        if (right and top) or (left and bottom):
            return Qt.CursorShape.SizeBDiagCursor
        if left or right:
            return Qt.CursorShape.SizeHorCursor
        if top or bottom:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    # ---------------------------------------------------------------- 拖动

    def apply_resize(self, global_pos: QPoint) -> None:
        if not self._edges:
            return

        delta = global_pos - self._origin
        geometry = QRect(self._start_geometry)
        min_width = self._window.minimumWidth()
        min_height = self._window.minimumHeight()

        if self._edges & Qt.Edge.LeftEdge:
            geometry.setLeft(
                min(
                    geometry.right() - min_width + 1,
                    geometry.left() + delta.x(),
                )
            )
        elif self._edges & Qt.Edge.RightEdge:
            geometry.setRight(
                max(
                    geometry.left() + min_width - 1,
                    geometry.right() + delta.x(),
                )
            )
        if self._edges & Qt.Edge.TopEdge:
            geometry.setTop(
                min(
                    geometry.bottom() - min_height + 1,
                    geometry.top() + delta.y(),
                )
            )
        elif self._edges & Qt.Edge.BottomEdge:
            geometry.setBottom(
                max(
                    geometry.top() + min_height - 1,
                    geometry.bottom() + delta.y(),
                )
            )
        self._window.setGeometry(geometry)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if not isinstance(watched, QWidget) or watched.window() is not self._window:
            return super().eventFilter(watched, event)

        event_type = event.type()
        if (
            event_type == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            edges = self.edges_at(
                watched.mapTo(self._window, event.position().toPoint())
            )
            if edges:
                self._edges = edges
                self._origin = event.globalPosition().toPoint()
                self._start_geometry = self._window.geometry()
                self._window.setCursor(self.cursor_for_edges(edges))
                self._window.grabMouse()
                return True
        elif event_type == QEvent.Type.MouseMove:
            if self._edges:
                self.apply_resize(event.globalPosition().toPoint())
                return True
            edges = self.edges_at(
                watched.mapTo(self._window, event.position().toPoint())
            )
            if edges:
                self._window.setCursor(self.cursor_for_edges(edges))
            else:
                self._window.unsetCursor()
        elif event_type == QEvent.Type.MouseButtonRelease and self._edges:
            self._edges = Qt.Edge(0)
            self._window.releaseMouse()
            self._window.unsetCursor()
            return True
        elif event_type == QEvent.Type.UngrabMouse:
            self._edges = Qt.Edge(0)
        return super().eventFilter(watched, event)
