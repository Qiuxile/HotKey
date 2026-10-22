"""主窗口冒烟测试。"""

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtTest import QTest

from hotkey.ui.main_window import MainWindow
from hotkey.ui.widgets.block_editor import BlockListEditor
from hotkey.ui.widgets.statement_tree import StatementTree


def make_window(qtbot, tmp_path):
    window = MainWindow(tmp_path, with_tray=False)
    qtbot.addWidget(window)
    return window


def test_main_window_builds(qtbot, tmp_path):
    window = make_window(qtbot, tmp_path)

    assert "HotKey" in window.windowTitle()
    model = window.ui.hotkeyTable.model()
    assert model.columnCount() == 3
    assert model.headerData(0, Qt.Orientation.Horizontal) == "名称"
    assert window.ui.editorPanel.isHidden()
    assert window.ui.editorTabs.count() == 0
    assert window.menuWidget() is not None


def test_default_narrow_window_is_400x600(qtbot, tmp_path):
    window = make_window(qtbot, tmp_path)
    window.show()
    qtbot.wait(50)

    assert window.width() == 400
    assert window.height() == 600
    assert window.ui.editorPanel.isHidden()


def test_editor_expands_only_from_default_size(qtbot, tmp_path):
    window = make_window(qtbot, tmp_path)
    window.show()
    qtbot.wait(50)

    window._set_editor_visible(True)
    assert not window.ui.editorPanel.isHidden()
    assert window.size() == QSize(1240, 600)

    window._set_editor_visible(False)
    assert window.size() == QSize(400, 600)


def test_editor_does_not_reset_user_window(qtbot, tmp_path):
    window = make_window(qtbot, tmp_path)
    window.show()
    qtbot.wait(50)
    window.resize(900, 700)

    window._set_editor_visible(True)
    assert not window.ui.editorPanel.isHidden()
    assert window.size() == QSize(900, 700)

    window._set_editor_visible(False)
    assert window.size() == QSize(900, 700)


def test_promoted_widgets_are_used(qtbot, tmp_path):
    window = make_window(qtbot, tmp_path)

    assert isinstance(window.ui.blockEditor, BlockListEditor)
    assert isinstance(window.ui.statementTree, StatementTree)
    # 顶部「空」+ 6 个分类
    assert window.ui.statementTree.topLevelItemCount() == 7


def test_editor_toggle(qtbot, tmp_path):
    window = make_window(qtbot, tmp_path)
    window.show()

    window._set_editor_visible(True)
    assert not window.ui.editorPanel.isHidden()
    assert window.ui.actionToggleEditor.isChecked()

    window._set_editor_visible(False)
    assert window.ui.editorPanel.isHidden()
    assert not window.ui.actionToggleEditor.isChecked()


def test_titlebar_has_menu_and_toolbar_is_above_blocks(qtbot, tmp_path):
    window = make_window(qtbot, tmp_path)
    window.show()
    qtbot.wait(50)

    assert len(window.title_bar.menu_buttons) == 3
    assert all(button.isVisible() for button in window.title_bar.menu_buttons)
    assert len(window.title_bar.menus[0].actions()) >= 4
    QTest.mouseClick(
        window.title_bar.menu_buttons[0], Qt.MouseButton.LeftButton
    )
    qtbot.wait(10)
    assert window.title_bar.menus[0].isVisible()
    window.title_bar.menus[0].hide()

    window._set_editor_visible(True)
    qtbot.wait(10)
    toolbar_y = window.ui.btnCapturePos.mapTo(window, QPoint(0, 0)).y()
    editor_y = window.ui.blockEditor.mapTo(window, QPoint(0, 0)).y()
    assert toolbar_y < editor_y


def test_resize_edges(qtbot, tmp_path):
    window = make_window(qtbot, tmp_path)
    window.show()
    qtbot.wait(50)
    window.resize(800, 600)

    top_left = window.resizer.edges_at(QPoint(1, 1))
    assert top_left & Qt.Edge.LeftEdge
    assert top_left & Qt.Edge.TopEdge
    assert (
        window.resizer.cursor_for_edges(top_left)
        == Qt.CursorShape.SizeFDiagCursor
    )

    bottom_right = window.resizer.edges_at(QPoint(799, 599))
    assert bottom_right & Qt.Edge.RightEdge
    assert bottom_right & Qt.Edge.BottomEdge

    assert not window.resizer.edges_at(QPoint(400, 300))
    assert (
        window.resizer.cursor_for_edges(Qt.Edge.LeftEdge)
        == Qt.CursorShape.SizeHorCursor
    )


def test_manual_resize_geometry(qtbot, tmp_path):
    window = make_window(qtbot, tmp_path)
    window.setGeometry(100, 100, 800, 600)
    window.resizer._start_geometry = window.geometry()
    window.resizer._origin = QPoint(900, 700)
    window.resizer._edges = Qt.Edge.RightEdge | Qt.Edge.BottomEdge

    window.resizer.apply_resize(QPoint(950, 760))

    assert window.geometry().width() == 850
    assert window.geometry().height() == 660


def test_script_roundtrip_through_window(qtbot, tmp_path):
    from hotkey.core import blocks, storage
    from hotkey.core.models import Block, HotKey

    storage.save(
        tmp_path / "demo.hk",
        [
            HotKey(
                key="ctrl+1",
                description="测试",
                script="x = 1",
                id="fixed",
                blocks=[Block("empty", text="x = 1")],
            )
        ],
    )

    window = make_window(qtbot, tmp_path)

    assert window.ui.hotkeyTable.model().rowCount() == 1
    entry = window._model.entry(0)
    assert entry.id == "fixed"
    assert entry.name == "demo"

    window._open_editor_for_id("fixed")
    assert window.ui.editorTabs.count() == 1
    blocks_ = window.ui.blockEditor.blocks()
    assert blocks_[0].kind == "empty"
    assert blocks_[0].text == "x = 1"
    assert blocks.blocks_to_code(blocks_) == "x = 1"
