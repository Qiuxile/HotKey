"""主菜单组件。"""

import json
import logging
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, List, TYPE_CHECKING

from hotkey.config import (
    SEARCH_DEBOUNCE_MS, ANIMATION_STEP_PX,
    ANIMATION_INTERVAL_MS, SEARCH_HIDDEN_Y, ANIMATION_EASING,
    COLOR_BG_SEARCH, COLOR_FG_PRIMARY, COLOR_FG_PLACEHOLDER,
    COLOR_ACCENT, COLOR_SHADOW, COLOR_BORDER,
)

if TYPE_CHECKING:
    from hotkey.ui.tree import HotKeyTree
    from hotkey.actuator import HotKeyActuator

logger = logging.getLogger('HotKey.MenuBar')

# 条件导入
try:
    import keyboard
except ImportError:
    keyboard = None

try:
    import pystray
    from PIL import Image
except ImportError:
    pystray = None
    Image = None


class MenuBar(tk.Menu):
    """主菜单组件，提供所有功能入口。"""

    def __init__(self, master: Optional[tk.Widget] = None,
                 tree: Optional['HotKeyTree'] = None,
                 actuator: Optional['HotKeyActuator'] = None):
        super().__init__(master, tearoff=False)
        self._tree = tree
        self._actuator = actuator
        self._search_frame: Optional[ttk.Frame] = None
        self._search_entry: Optional[ttk.Entry] = None
        self._search_after_id: Optional[str] = None
        self._anim_after_id: Optional[str] = None
        self._anim_cancelled = False

        self._create_menus()

    def _create_menus(self) -> None:
        file_menu = tk.Menu(self, tearoff=False)
        file_menu.add_command(label="导入", command=self._import_json, accelerator="Ctrl+O")
        file_menu.add_command(label="保存", command=self._save_json, accelerator="Ctrl+S")
        file_menu.add_command(label="导出", command=self._export_json,
                              accelerator="Ctrl+Shift+S")
        self.add_cascade(label="文件", menu=file_menu)

        edit_menu = tk.Menu(self, tearoff=False)
        edit_menu.add_command(label="添加热键", command=self._add_hotkey,
                              accelerator="Ctrl+N")
        self.add_cascade(label="编辑", menu=edit_menu)

        action_menu = tk.Menu(self, tearoff=False)
        action_menu.add_command(label="搜索", command=self._toggle_search,
                                accelerator="Ctrl+F")
        action_menu.add_separator()
        action_menu.add_command(label="启动监听", command=self._start_hotkey)
        action_menu.add_command(label="停止监听", command=self._stop_hotkey)
        self.add_cascade(label="操作", menu=action_menu)

    def _add_hotkey(self) -> None:
        if self._tree and hasattr(self._tree, '_app') and self._tree._app:
            self._tree._app.add_hotkey_dialog()

    def _save_json(self) -> None:
        if self._tree and hasattr(self._tree, '_app') and self._tree._app:
            self._tree._app.export_json_dialog()

    def _import_json(self) -> None:
        if not self._tree:
            return
        file_path = filedialog.askopenfilename(
            title="选择JSON文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialdir="jsons"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                hotkeys = json.load(f)
            if not isinstance(hotkeys, list):
                raise ValueError("JSON文件格式不正确，应为数组")
            # JSON Schema 验证
            valid_hotkeys = []
            for i, hk in enumerate(hotkeys):
                if not isinstance(hk, dict):
                    logger.warning("跳过非字典条目 #%d", i)
                    continue
                if 'key' not in hk or not isinstance(hk['key'], str) or not hk['key']:
                    logger.warning("跳过缺少有效 key 的条目 #%d", i)
                    continue
                if 'code' in hk and not isinstance(hk['code'], list):
                    hk['code'] = []
                valid_hotkeys.append(hk)

            if len(valid_hotkeys) < len(hotkeys):
                messagebox.showwarning(
                    "部分导入",
                    f"共 {len(hotkeys)} 条记录，{len(valid_hotkeys)} 条有效，"
                    f"{len(hotkeys) - len(valid_hotkeys)} 条格式错误已跳过"
                )

            self._tree.load_hotkeys(valid_hotkeys)
            messagebox.showinfo("成功", f"成功导入 {len(valid_hotkeys)} 个热键配置")
        except json.JSONDecodeError as e:
            logger.error("JSON解析失败: %s", e)
            messagebox.showerror("错误", f"JSON解析失败: {str(e)}")
        except Exception as e:
            logger.error("导入失败: %s", e, exc_info=True)
            messagebox.showerror("错误", f"导入失败: {str(e)}")

    def _export_json(self) -> None:
        if not self._tree:
            return
        hotkeys = self._tree.get_hotkeys()
        if not hotkeys:
            messagebox.showwarning("提示", "没有热键可导出")
            return
        file_path = filedialog.asksaveasfilename(
            title="保存JSON文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialdir="jsons",
            defaultextension=".json",
            initialfile="hotkeys.json"
        )
        if not file_path:
            return
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            # 原子写入：先写临时文件，再替换
            tmp_path = file_path + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(hotkeys, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, file_path)
            messagebox.showinfo("成功", f"成功导出 {len(hotkeys)} 个热键配置")
        except OSError as e:
            logger.error("文件写入失败: %s", e)
            messagebox.showerror("错误", f"文件写入失败: {str(e)}")
        except Exception as e:
            logger.error("导出失败: %s", e, exc_info=True)
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def _start_hotkey(self) -> None:
        if self._tree and self._actuator and hasattr(self._tree, '_app') and self._tree._app:
            self._tree._app.start_hotkey_listening()

    def _stop_hotkey(self) -> None:
        if self._actuator:
            self._actuator.stop()
            messagebox.showinfo("已停止", "热键监听已停止")

    def _toggle_search(self) -> None:
        if not self._search_frame:
            self._create_search_widgets()
        # 取消进行中的动画
        self._anim_cancelled = True
        if self._anim_after_id:
            self.master.after_cancel(self._anim_after_id)
        width = int(self.master.winfo_width() * 0.94)
        x = int((self.master.winfo_width() - width) / 2)
        self._search_frame.config(width=width)
        self._search_frame.place(x=x, y=SEARCH_HIDDEN_Y)
        self._search_frame.lift()
        self._move_to_visible()
        self.master.update_idletasks()
        self._search_entry.focus_set()

    def _create_search_widgets(self) -> None:
        self._search_frame = tk.Frame(self.master, height=38,
                                       bg=COLOR_BG_SEARCH,
                                       highlightbackground=COLOR_BORDER,
                                       highlightthickness=1)
        self._search_frame.pack_propagate(False)

        self._search_entry = tk.Entry(self._search_frame,
                                       font=('Microsoft YaHei UI', 10),
                                       bg=COLOR_BG_SEARCH,
                                       fg=COLOR_FG_PRIMARY,
                                       insertbackground=COLOR_ACCENT,
                                       relief='flat',
                                       borderwidth=0,
                                       highlightthickness=0)
        self._search_entry.pack(side='top', fill='x', padx=14, pady=9, expand=True)
        self._search_entry.insert(0, "输入搜索内容...")
        self._search_entry.config(fg=COLOR_FG_PLACEHOLDER)

        self._search_entry.bind('<KeyRelease>', self._on_search_change)
        self._search_entry.bind('<FocusIn>', self._on_search_focus_in)
        self._search_entry.bind('<FocusOut>', self._on_search_focus_out)

    def _on_search_change(self, event: tk.Event) -> None:
        if self._search_after_id:
            self.master.after_cancel(self._search_after_id)
        self._search_after_id = self.master.after(
            SEARCH_DEBOUNCE_MS, self._do_search
        )

    def _do_search(self) -> None:
        self._search_after_id = None
        if self._tree:
            self._tree.search_hotkeys(self._search_entry.get())

    def _on_search_focus_in(self, event: tk.Event) -> None:
        self._clear_placeholder()
        self._search_entry.config(fg=COLOR_FG_PRIMARY)
        self._move_to_visible()

    def _on_search_focus_out(self, event: tk.Event) -> None:
        if not self._search_entry.get().strip():
            self._search_entry.delete(0, tk.END)
            self._search_entry.insert(0, "输入搜索内容...")
            self._search_entry.config(fg=COLOR_FG_PLACEHOLDER)
        self._move_to_hidden()

    def _clear_placeholder(self) -> None:
        if self._search_entry.get() == "输入搜索内容...":
            self._search_entry.delete(0, tk.END)

    def _move_to_visible(self) -> None:
        self._anim_cancelled = False
        self._animate_move(0)

    def _move_to_hidden(self) -> None:
        self._anim_cancelled = False
        self._animate_move(SEARCH_HIDDEN_Y)

    def _animate_move(self, target_y: int) -> None:
        if self._anim_cancelled or not self._search_frame:
            return

        current_y = self._search_frame.winfo_y()
        if abs(current_y - target_y) < 2:
            self._search_frame.place(y=target_y)
            return

        # 缓动动画：每帧移动剩余距离的 (1 - EASING) 倍
        delta = (target_y - current_y) * (1.0 - ANIMATION_EASING)
        if abs(delta) < 1:
            delta = 1 if delta > 0 else -1
        new_y = current_y + delta

        if (delta > 0 and new_y >= target_y) or (delta < 0 and new_y <= target_y):
            new_y = target_y

        self._search_frame.place(x=self._search_frame.winfo_x(), y=int(new_y))

        if new_y != target_y:
            self._anim_after_id = self.master.after(
                ANIMATION_INTERVAL_MS, self._animate_move, target_y
            )
