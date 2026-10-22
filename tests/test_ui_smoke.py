"""主窗口冒烟测试。"""

from hotkey.ui.main_window import MainWindow
from hotkey.ui.widgets.script_editor import ScriptEditor


def test_main_window_builds(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle().startswith("HotKey")
    assert window.ui.hotkeyTable.model().columnCount() == 2
    assert window.ui.editorPanel.isHidden()


def test_promoted_widget_is_used(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert isinstance(window.ui.scriptEditor, ScriptEditor)


def test_editor_toggle(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window._set_editor_visible(True)
    assert not window.ui.editorPanel.isHidden()
    assert window.ui.actionToggleEditor.isChecked()

    window._set_editor_visible(False)
    assert window.ui.editorPanel.isHidden()
    assert not window.ui.actionToggleEditor.isChecked()
