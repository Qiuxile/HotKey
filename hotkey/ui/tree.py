"""热键列表树组件。"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional, Protocol

from hotkey.config import KEY_NAME_MAP, MODIFIER_MASKS, MODIFIER_KEYSYMS
from hotkey.config import (
    COLOR_BG_MAIN, COLOR_BG_HEADER, COLOR_BG_SIDEBAR,
    COLOR_FG_PRIMARY, COLOR_FG_HEADER,
    COLOR_SELECTION, COLOR_ROW_ALT, COLOR_ACCENT, COLOR_BORDER,
    COLOR_BUTTON, COLOR_BUTTON_TEXT,
)

logger = logging.getLogger('HotKey.Tree')


class AppCallback(Protocol):
    """App 回调接口协议，避免循环导入。"""
    def open_code_editor(self, index: int) -> None: ...
    def add_hotkey_dialog(self) -> None: ...
    def start_single_hotkey(self, index: int) -> None: ...


class HotKeyTree(ttk.Frame):
    """热键列表树组件，用于显示和管理热键数据。"""

    def __init__(self, master: Optional[tk.Widget] = None,
                 app: Optional[AppCallback] = None):
        super().__init__(master, padding=5, width=350)
        self._hotkeys: List[Dict[str, Any]] = []
        self._app = app
        self._selected_index = -1
        self._item_index_map: Dict[str, int] = {}
        self.grid_propagate(False)

        # TreeView 主题样式
        style = ttk.Style()
        style.configure('Hotkey.Treeview',
                        background=COLOR_BG_MAIN,
                        foreground=COLOR_FG_PRIMARY,
                        fieldbackground=COLOR_BG_MAIN,
                        rowheight=28,
                        borderwidth=0)
        style.configure('Hotkey.Treeview.Heading',
                        background=COLOR_BG_HEADER,
                        foreground=COLOR_FG_HEADER,
                        font=('Microsoft YaHei UI', 9, 'bold'),
                        borderwidth=0,
                        padding=(8, 6))
        style.map('Hotkey.Treeview.Heading',
                  background=[('active', '#4a5e78')])
        style.map('Hotkey.Treeview',
                  background=[('selected', COLOR_SELECTION)],
                  foreground=[('selected', COLOR_FG_PRIMARY)])

        columns = ("hotkey", "description")
        self._tree = ttk.Treeview(self, columns=columns, show="headings",
                                  style='Hotkey.Treeview')
        self._tree.heading("hotkey", text="热键")
        self._tree.heading("description", text="描述")
        self._tree.column("hotkey", width=140, anchor=tk.CENTER)
        self._tree.column("description", stretch=True)

        # 交替行标签
        self._tree.tag_configure('odd', background=COLOR_BG_MAIN)
        self._tree.tag_configure('even', background=COLOR_ROW_ALT)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._tree.bind("<Button-3>", self._show_context_menu)

        self._context_menu = tk.Menu(self, tearoff=False)
        self._context_menu.add_command(label="编辑", command=self._edit_hotkey)
        self._context_menu.add_command(label="修改", command=self._modify_hotkey)
        self._context_menu.add_command(label="删除", command=self._delete_hotkey)
        self._context_menu.add_command(label="添加", command=self._add_hotkey)
        self._context_menu.add_command(label="启动", command=self._start_hotkey)

    def _show_context_menu(self, event: tk.Event) -> None:
        try:
            item = self._tree.identify_row(event.y)
            if item:
                self._tree.selection_set(item)
                children = self._tree.get_children()
                self._selected_index = children.index(item) if item in children else -1
                self._context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            logger.debug("右键菜单显示失败: %s", e)

    def _edit_hotkey(self) -> None:
        if self._app and self._selected_index >= 0:
            self._app.open_code_editor(self._selected_index)

    def _modify_hotkey(self) -> None:
        if self._selected_index < 0 or self._selected_index >= len(self._hotkeys):
            return

        hotkey = self._hotkeys[self._selected_index]
        current_key = hotkey.get('key', '')
        current_desc = hotkey.get('description', '')

        dialog = tk.Toplevel(self.master)
        dialog.title("修改热键")
        dialog.geometry("340x170")
        dialog.resizable(False, False)
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.configure(bg=COLOR_BG_MAIN)

        new_key = [current_key]
        is_listening = [False]

        key_frame = ttk.Frame(dialog, padding=10)
        key_frame.pack(fill="x", padx=5)
        ttk.Label(key_frame, text="热键:").grid(row=0, column=0, sticky="w", padx=5)
        key_entry = ttk.Entry(key_frame, width=25)
        key_entry.insert(0, current_key)
        key_entry.grid(row=0, column=1, sticky="ew", padx=5)

        desc_frame = ttk.Frame(dialog, padding=10)
        desc_frame.pack(fill="x", padx=5)
        ttk.Label(desc_frame, text="描述:").grid(row=0, column=0, sticky="w", padx=5)
        desc_entry = ttk.Entry(desc_frame, width=35)
        desc_entry.insert(0, current_desc)
        desc_entry.grid(row=0, column=1, sticky="ew", padx=5)
        desc_frame.grid_columnconfigure(1, weight=1)

        def on_key_press(event: tk.Event) -> str:
            if not is_listening[0]:
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
            key_entry.delete(0, tk.END)
            key_entry.insert(0, key_str)
            new_key[0] = key_str
            return "break"

        def on_focus_in(event: tk.Event) -> None:
            is_listening[0] = True

        def on_focus_out(event: tk.Event) -> None:
            is_listening[0] = False

        key_entry.bind('<FocusIn>', on_focus_in)
        key_entry.bind('<FocusOut>', on_focus_out)
        dialog.bind_class('Toplevel', '<KeyPress>', on_key_press, add='+')

        def cleanup() -> None:
            try:
                dialog.unbind_class('Toplevel', '<KeyPress>')
            except Exception:
                pass

        def confirm() -> None:
            key = new_key[0].strip()
            desc = desc_entry.get().strip()
            if not key:
                messagebox.showwarning("提示", "请点击热键框后按下热键", parent=dialog)
                return
            self._hotkeys[self._selected_index]['key'] = key
            self._hotkeys[self._selected_index]['description'] = desc
            self.load_hotkeys(self._hotkeys)
            cleanup()
            dialog.destroy()

        btn_frame = ttk.Frame(dialog, padding=10)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="确定", command=confirm).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="取消",
                   command=lambda: [cleanup(), dialog.destroy()]).pack(side="right", padx=5)

        dialog.protocol("WM_DELETE_WINDOW", lambda: [cleanup(), dialog.destroy()])
        desc_entry.focus_set()

    def _delete_hotkey(self) -> None:
        if self._selected_index >= 0 and self._selected_index < len(self._hotkeys):
            confirm = messagebox.askyesno("确认删除", "确定要删除这个热键吗？")
            if confirm:
                selected_item = self._tree.selection()
                if selected_item:
                    self._tree.delete(selected_item[0])
                del self._hotkeys[self._selected_index]
                if self._selected_index >= len(self._hotkeys):
                    self._selected_index = len(self._hotkeys) - 1

    def _add_hotkey(self) -> None:
        if self._app:
            self._app.add_hotkey_dialog()

    def _start_hotkey(self) -> None:
        if self._selected_index >= 0 and self._selected_index < len(self._hotkeys):
            if self._app:
                self._app.start_single_hotkey(self._selected_index)

    def load_hotkeys(self, hotkeys: List[Dict[str, Any]]) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._hotkeys = hotkeys
        self._item_index_map.clear()
        for i, hotkey in enumerate(hotkeys):
            key = hotkey.get("key", "")
            description = hotkey.get("description", "")
            tag = 'even' if i % 2 == 0 else 'odd'
            item_id = self._tree.insert("", tk.END, values=(key, description), tags=(tag,))
            self._item_index_map[item_id] = i

    def get_hotkeys(self) -> List[Dict[str, Any]]:
        return self._hotkeys.copy()

    def search_hotkeys(self, search_text: str) -> None:
        search_text = search_text.lower().strip()
        for item in self._tree.get_children():
            self._tree.delete(item)
        for hotkey in self._hotkeys:
            key = hotkey.get("key", "").lower()
            description = hotkey.get("description", "").lower()
            if not search_text or search_text in key or search_text in description:
                self._tree.insert("", tk.END,
                                  values=(hotkey.get("key"), hotkey.get("description")))
