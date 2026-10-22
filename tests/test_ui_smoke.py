"""主窗口冒烟测试。"""

from hotkey.ui.main_window import MainWindow
from hotkey.ui.widgets.block_tree import BlockTree
from hotkey.ui.widgets.statement_tree import StatementTree


def make_window(qtbot, tmp_path):
    window = MainWindow(tmp_path / "hotkeys.json", with_tray=False)
    qtbot.addWidget(window)
    return window


def test_main_window_builds(qtbot, tmp_path):
    window = make_window(qtbot, tmp_path)

    assert window.windowTitle().startswith("HotKey")
    assert window.ui.hotkeyTable.model().columnCount() == 3
    assert window.ui.editorPanel.isHidden()


def test_promoted_widgets_are_used(qtbot, tmp_path):
    window = make_window(qtbot, tmp_path)

    assert isinstance(window.ui.blockTree, BlockTree)
    assert isinstance(window.ui.statementTree, StatementTree)
    # 顶部「空」+ 5 个分类
    assert window.ui.statementTree.topLevelItemCount() == 6


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
                blocks=[Block("empty", "x = 1")],
            )
        ],
    )

    window = MainWindow(config, with_tray=False)
    qtbot.addWidget(window)

    assert window.ui.hotkeyTable.model().rowCount() == 1
    entry = window._model.entry(0)
    assert entry.id == "fixed"

    window._open_editor_for_id("fixed")
    assert window.ui.blockTree.topLevelItemCount() == 1
    row = window.ui.blockTree.itemWidget(
        window.ui.blockTree.topLevelItem(0), 0
    )
    assert row.code_edit().text() == "x = 1"
    assert blocks.blocks_to_code(entry.blocks) == "x = 1"
