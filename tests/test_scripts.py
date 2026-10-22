"""脚本编辑标签、保存、无热键脚本、窗口外观。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from hotkey.core import storage
from hotkey.core.models import Block, HotKey
from hotkey.ui import theme as theme_module
from hotkey.ui.main_window import MainWindow


def make_script(tmp_path, name, key="", blocks=None):
    path = tmp_path / f"{name}.hk"
    storage.save(
        path,
        [
            HotKey(
                key=key,
                id=name,
                blocks=blocks if blocks is not None else [Block("empty", text="x = 1")],
            )
        ],
    )
    return path


def make_window(qtbot, path):
    window = MainWindow(path, with_tray=False)
    qtbot.addWidget(window)
    return window


def ids(window):
    return [entry.id for entry in window._model.entries()]


def test_open_two_scripts_as_tabs(qtbot, tmp_path):
    make_script(tmp_path, "alpha", "ctrl+a")
    make_script(tmp_path, "beta", "ctrl+b")
    window = make_window(qtbot, tmp_path)
    alpha, beta = ids(window)

    window._open_editor_for_id(alpha)
    window._open_editor_for_id(beta)

    assert window.ui.editorTabs.count() == 2
    assert not window.ui.editorPanel.isHidden()

    window.ui.editorTabs.setCurrentIndex(0)
    assert window.ui.blockEditor.blocks()[0].text == "x = 1"

    window.ui.editorTabs.setCurrentIndex(1)
    assert window._current_id == beta


def test_save_tab_writes_single_file(qtbot, tmp_path):
    path = make_script(tmp_path, "alpha", "ctrl+a")
    window = make_window(qtbot, tmp_path)
    window._open_editor_for_id(ids(window)[0])

    window.ui.blockEditor.add_snippet("mouse_click")
    window._save_current_tab()

    loaded = storage.load(path)
    assert len(loaded[0].blocks) == 2
    assert loaded[0].script == "x = 1\npyautogui.click()"


def test_script_without_hotkey(qtbot, tmp_path):
    make_script(tmp_path, "plain", "")
    window = make_window(qtbot, tmp_path)

    entry = window._model.entry(0)
    assert entry.key == ""
    assert window._model.data(window._model.index(0, 1)) == "—"
    assert window._executable_entries() == []


def test_frameless_window_and_title_bar(qtbot, tmp_path):
    make_script(tmp_path, "alpha")
    window = make_window(qtbot, tmp_path)

    assert window.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert window.title_bar is not None
    assert window.title_bar.title_label.text()


def test_theme_toggle_and_persistence(qtbot, tmp_path):
    theme_module.save_theme("light")
    theme_module.apply_theme(QApplication.instance(), "light")
    make_script(tmp_path, "alpha")
    window = make_window(qtbot, tmp_path)

    try:
        assert window.ui.actionTheme.isChecked() is False

        window._toggle_theme()
        assert theme_module.current_theme() == "dark"
        assert "#0B0C15" in QApplication.instance().styleSheet()
        assert window.ui.actionTheme.isChecked() is True

        window._toggle_theme()
        assert theme_module.current_theme() == "light"
        assert "#F9FAFB" in QApplication.instance().styleSheet()
    finally:
        theme_module.save_theme("light")
        theme_module.apply_theme(QApplication.instance(), "light")
