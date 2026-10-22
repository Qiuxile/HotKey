"""热键录入对话框测试。"""

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QDialog

from hotkey.ui.recorder import HotKeyDialog


def test_dialog_converts_qt_sequence(qtbot):
    dialog = HotKeyDialog()
    qtbot.addWidget(dialog)

    dialog.ui.keySequenceEdit.setKeySequence(QKeySequence("Ctrl+Shift+A"))
    dialog.ui.descriptionEdit.setText("测试描述")
    dialog._on_accept()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.hotkey_key() == "ctrl+shift+a"
    assert dialog.hotkey_description() == "测试描述"


def test_dialog_prefills_existing_key(qtbot):
    dialog = HotKeyDialog(key="ctrl+alt+f9", description="旧描述")
    qtbot.addWidget(dialog)

    text = dialog.ui.keySequenceEdit.keySequence().toString()
    assert text == "Ctrl+Alt+F9"
    assert dialog.ui.descriptionEdit.text() == "旧描述"
