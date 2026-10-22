"""主窗口冒烟测试。"""

from hotkey.ui.main_window import MainWindow
from hotkey.ui.widgets.script_editor import ScriptEditor
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

    assert isinstance(window.ui.scriptEditor, ScriptEditor)
    assert isinstance(window.ui.statementTree, StatementTree)
    assert window.ui.statementTree.topLevelItemCount() == 5


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
    from hotkey.core import storage
    from hotkey.core.models import HotKey

    config = tmp_path / "hotkeys.json"
    storage.save(config, [HotKey(key="ctrl+1", description="测试", script="x = 1", id="fixed")])

    window = MainWindow(config, with_tray=False)
    qtbot.addWidget(window)

    assert window.ui.hotkeyTable.model().rowCount() == 1
    assert window._model.entry(0).id == "fixed"
