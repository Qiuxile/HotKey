"""热键录制器 - 统一的键盘事件处理模块。

消除 _modify_hotkey 和 add_hotkey_dialog 中的重复代码。
"""

import tkinter as tk
from typing import Optional, Callable

from hotkey.config import KEY_NAME_MAP, MODIFIER_MASKS, MODIFIER_KEYSYMS


class KeyRecorder:
    """热键录制器，封装键盘事件捕获逻辑。

    使用方式:
        recorder = KeyRecorder(callback=lambda key: print(key))
        recorder.attach(dialog)  # 在对话框上开始监听
        ...
        recorder.detach(dialog)  # 停止监听
    """

    def __init__(self, callback: Callable[[str], None]):
        self._callback = callback
        self._current_key: str = ""
        self._is_listening: bool = False
        self._bound_widget: Optional[tk.Widget] = None
        self._on_key_press_id: Optional[str] = None

    @property
    def current_key(self) -> str:
        return self._current_key

    def start_listening(self, widget: tk.Widget) -> None:
        """在指定 widget 上开始监听键盘事件。"""
        self._is_listening = True
        self._current_key = ""
        self._bound_widget = widget
        # 使用 bind_class 限定范围，避免 bind_all 的全局泄露
        self._on_key_press_id = widget.bind_class(
            'Toplevel', '<KeyPress>', self._on_key_press, add='+'
        )

    def stop_listening(self, widget: tk.Widget) -> None:
        """停止监听并解绑事件。"""
        self._is_listening = False
        if self._bound_widget and self._on_key_press_id:
            try:
                widget.unbind_class('Toplevel', '<KeyPress>')
            except Exception:
                pass
        self._bound_widget = None
        self._on_key_press_id = None

    def _on_key_press(self, event: tk.Event) -> str:
        """处理键盘按下事件。"""
        if not self._is_listening:
            return "break"

        if event.keysym in MODIFIER_KEYSYMS:
            return "break"

        keys = []
        for mask, name in MODIFIER_MASKS.items():
            if event.state & mask:
                keys.append(name)

        key_name = event.keysym.lower()
        key_name = KEY_NAME_MAP.get(key_name, key_name)
        keys.append(key_name)

        key_str = '+'.join(keys)
        self._current_key = key_str
        self._callback(key_str)
        return "break"
