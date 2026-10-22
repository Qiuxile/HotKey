"""热键录入对话框。"""

from __future__ import annotations

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QDialog, QMessageBox

from hotkey.core import keymap
from hotkey.ui.generated.ui_hotkey_dialog import Ui_HotKeyDialog


class HotKeyDialog(QDialog):
    def __init__(self, parent=None, key: str = "", description: str = "") -> None:
        super().__init__(parent)
        self.ui = Ui_HotKeyDialog()
        self.ui.setupUi(self)

        self._key = ""
        if key:
            self.ui.keySequenceEdit.setKeySequence(
                QKeySequence(keymap.keyboard_to_qt(key))
            )
        self.ui.descriptionEdit.setText(description)

        self.ui.buttonBox.accepted.connect(self._on_accept)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.ui.descriptionEdit.setFocus()

    def hotkey_key(self) -> str:
        return self._key

    def hotkey_description(self) -> str:
        return self.ui.descriptionEdit.text().strip()

    def _on_accept(self) -> None:
        sequence = self.ui.keySequenceEdit.keySequence()
        text = sequence.toString(QKeySequence.SequenceFormat.PortableText)

        if not text or "," in text:
            QMessageBox.warning(
                self,
                "热键无效",
                "请只按一个组合键，例如 Ctrl+Shift+A。",
            )
            return

        converted = keymap.qt_to_keyboard(text)
        if converted is None or keymap.is_modifier_only(converted):
            QMessageBox.warning(
                self,
                "热键无效",
                f"无法识别这个按键：{text}",
            )
            return

        self._key = converted
        self.accept()
