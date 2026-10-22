"""多文件标签页与主题切换。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from hotkey.core import storage
from hotkey.core.models import HotKey
from hotkey.ui import theme as theme_module
from hotkey.ui.main_window import MainWindow


def write_file(path, key):
    storage.save(path, [HotKey(key=key, id=key)])
    return path


def make_window(qtbot, path):
    window = MainWindow(path, with_tray=False)
    qtbot.addWidget(window)
    return window


def test_open_multiple_files_as_tabs(qtbot, tmp_path):
    first = write_file(tmp_path / "a.json", "f1")
    second = write_file(tmp_path / "b.json", "f2")
    window = make_window(qtbot, first)

    assert window.ui.fileTabs.count() == 1
    assert window._model.entry(0).key == "f1"

    window._open_document_path(second)

    assert window.ui.fileTabs.count() == 2
    assert window.ui.fileTabs.currentIndex() == 1
    assert window._model.entry(0).key == "f2"

    window.ui.fileTabs.setCurrentIndex(0)
    assert window._model.entry(0).key == "f1"

    window.ui.fileTabs.setCurrentIndex(1)
    assert window._model.entry(0).key == "f2"


def test_new_untitled_document(qtbot, tmp_path):
    first = write_file(tmp_path / "a.json", "f1")
    window = make_window(qtbot, first)

    window._new_document()

    assert window.ui.fileTabs.count() == 2
    assert window._active_document().path is None
    assert window._model.rowCount() == 0


def test_autosave_active_document(qtbot, tmp_path):
    path = write_file(tmp_path / "a.json", "f1")
    window = make_window(qtbot, path)

    window._model.add(HotKey(key="f2", id="f2"))
    window._schedule_save()
    window._save_now()

    loaded = storage.load(path)
    assert [entry.key for entry in loaded] == ["f1", "f2"]


def test_switching_tabs_commits_changes(qtbot, tmp_path):
    first = write_file(tmp_path / "a.json", "f1")
    second = write_file(tmp_path / "b.json", "f2")
    window = make_window(qtbot, first)

    window._model.add(HotKey(key="f9", id="f9"))
    window._open_document_path(second)
    window.ui.fileTabs.setCurrentIndex(0)

    assert [entry.key for entry in window._model.entries()] == ["f1", "f9"]


def test_frameless_window_and_title_bar(qtbot, tmp_path):
    path = write_file(tmp_path / "a.json", "f1")
    window = make_window(qtbot, path)

    assert window.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert window.title_bar is not None
    assert "HotKey" in window.title_bar.title_label.text()


def test_theme_toggle_and_persistence(qtbot, tmp_path):
    theme_module.save_theme("light")
    theme_module.apply_theme(QApplication.instance(), "light")

    path = write_file(tmp_path / "a.json", "f1")
    window = make_window(qtbot, path)
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
