"""主窗口冒烟测试。"""

from hotkey.ui.main_window import MainWindow
from hotkey.ui.widgets.block_editor import BlockListEditor
from hotkey.ui.widgets.statement_tree import StatementTree


def make_window(qtbot, tmp_path):
    window = MainWindow(tmp_path / "hotkeys.json", with_tray=False)
    qtbot.addWidget(window)
    return window


def test_main_window_builds(qtbot, tmp_path):
    window = make_window(qtbot, tmp_path)

    assert "HotKey" in window.windowTitle()
    assert window.ui.hotkeyTable.model().columnCount() == 3
    assert window.ui.editorPanel.isHidden()
    assert window.ui.fileTabs.count() == 1
    assert window.ui.fileTabs.tabText(0) == "hotkeys.json"
    assert window.menuWidget() is not None


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


def test_config_roundtrip_through_window(qtbot, tmp_path):
    from hotkey.core import blocks
    from hotkey.core import storage
    from hotkey.core.models import Block, HotKey

    config = tmp_path / "hotkeys.json"
    storage.save(
        config,
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

    window = MainWindow(config, with_tray=False)
    qtbot.addWidget(window)

    assert window.ui.hotkeyTable.model().rowCount() == 1
    entry = window._model.entry(0)
    assert entry.id == "fixed"

    window._open_editor_for_id("fixed")
    blocks_ = window.ui.blockEditor.blocks()
    assert len(blocks_) == 1
    assert blocks_[0].kind == "empty"
    assert blocks_[0].text == "x = 1"
    assert blocks.blocks_to_code(blocks_) == "x = 1"
