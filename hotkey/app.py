"""应用程序主类。"""

import atexit
import json
import logging
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Any

from hotkey.actuator import HotKeyActuator
from hotkey.config import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, EDITOR_PANEL_WIDTH
from hotkey.config import (
    COLOR_BG_MAIN, COLOR_BG_SIDEBAR, COLOR_BG_EDITOR,
    COLOR_FG_PRIMARY, COLOR_FG_EDITOR, COLOR_FG_PLACEHOLDER,
    COLOR_ACCENT, COLOR_BUTTON, COLOR_BUTTON_TEXT, COLOR_BORDER,
)
from hotkey.models import DragState
from hotkey.ui.tree import HotKeyTree
from hotkey.ui.menubar import MenuBar

logger = logging.getLogger('HotKey.App')

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


class App:
    """主应用程序类，管理整个应用的生命周期。"""

    def __init__(self):
        self.root = tk.Tk()
        self._is_listening = False
        self._code_editor_frame = None
        self._code_text = None
        self._current_editing_index = -1
        self._original_width = DEFAULT_WINDOW_WIDTH
        self._editor_width = EDITOR_PANEL_WIDTH
        self._has_editor = False
        self._cleaned_up = False
        self._drag_data = DragState()

        self._setup_ui()
        self._setup_bindings()
        atexit.register(self._emergency_cleanup)
        # 启动 GUI 队列轮询
        self._poll_gui_queue()

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    @is_listening.setter
    def is_listening(self, value: bool) -> None:
        self._is_listening = value

    def _emergency_cleanup(self) -> None:
        if self._cleaned_up:
            return
        self._cleaned_up = True
        try:
            self.actuator.stop()
            if keyboard is not None:
                keyboard.unhook_all()
        except Exception as e:
            logger.error("紧急清理失败: %s", e)

    def _poll_gui_queue(self) -> None:
        """轮询 GUI 队列，将 pystray 线程的 GUI 操作安全转发到主线程。"""
        try:
            while True:
                func = self.actuator.gui_queue.get_nowait()
                func()
        except Exception:
            pass
        self.root.after(100, self._poll_gui_queue)

    def _setup_ui(self) -> None:
        self.root.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")
        self.root.title("HotKey - 热键工具")
        self.root.configure(background=COLOR_BG_MAIN)
        self.root.resizable(False, False)

        # 全局 ttk 主题样式
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=COLOR_BG_MAIN)
        style.configure('TLabel', background=COLOR_BG_MAIN, foreground=COLOR_FG_PRIMARY)
        style.configure('TButton',
                        background=COLOR_BUTTON, foreground=COLOR_BUTTON_TEXT,
                        borderwidth=0, focusthickness=0, padding=(14, 6),
                        font=('Microsoft YaHei UI', 9))
        style.map('TButton',
                  background=[('active', COLOR_ACCENT), ('pressed', '#3570c0')],
                  foreground=[('active', COLOR_BUTTON_TEXT)])
        style.configure('Editor.TFrame', background=COLOR_BG_SIDEBAR)
        style.configure('Editor.TLabel',
                        background=COLOR_BG_SIDEBAR, foreground=COLOR_FG_PRIMARY,
                        font=('Microsoft YaHei UI', 9, 'bold'))
        style.configure('Statement.Treeview',
                        background=COLOR_BG_SIDEBAR,
                        foreground=COLOR_FG_PRIMARY,
                        fieldbackground=COLOR_BG_SIDEBAR,
                        rowheight=26,
                        borderwidth=0,
                        font=('Microsoft YaHei UI', 9))
        style.map('Statement.Treeview',
                  background=[('selected', COLOR_ACCENT)],
                  foreground=[('selected', '#ffffff')])
        style.configure('Title.TLabel',
                        background=COLOR_BG_MAIN, foreground=COLOR_FG_PRIMARY,
                        font=('Microsoft YaHei UI', 10, 'bold'))

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(side="top", fill="both", expand=True)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=0, minsize=360)
        self.main_frame.grid_columnconfigure(1, weight=0, minsize=self._editor_width)

        self.actuator = HotKeyActuator(master=self.root, app=self)
        self.hotkey_tree = HotKeyTree(self.main_frame, app=self)
        self.menu_bar = MenuBar(self.root, self.hotkey_tree, self.actuator)
        self.root.config(menu=self.menu_bar)

        self.hotkey_tree.grid(row=0, column=0, sticky="nsew")
        self._create_code_editor()

    def _create_code_editor(self) -> None:
        self._code_editor_frame = ttk.Frame(self.main_frame, width=self._editor_width,
                                            style='Editor.TFrame')
        self._code_editor_frame.grid(row=0, column=1, sticky="nsew")
        self._code_editor_frame.grid_remove()
        self._code_editor_frame.grid_rowconfigure(0, weight=0)  # 工具栏
        self._code_editor_frame.grid_rowconfigure(1, weight=1)  # 内容区
        self._code_editor_frame.grid_columnconfigure(0, weight=1)
        self._code_editor_frame.grid_columnconfigure(1, weight=5)
        self._code_editor_frame.grid_propagate(False)

        # ── 顶部工具栏 ──
        toolbar = ttk.Frame(self._code_editor_frame, style='Editor.TFrame')
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(6, 4))
        toolbar.grid_columnconfigure(3, weight=1)  # 弹性空白

        ttk.Button(toolbar, text="🎯 捕获坐标",
                   command=self._capture_coordinate).grid(row=0, column=0, padx=2)
        ttk.Button(toolbar, text="🖍 捕获颜色",
                   command=self._capture_color).grid(row=0, column=1, padx=2)
        ttk.Button(toolbar, text="📐 屏幕尺寸",
                   command=self._insert_screen_size).grid(row=0, column=2, padx=2)

        ttk.Button(toolbar, text="保存", command=self._save_code).grid(
            row=0, column=4, padx=2)
        ttk.Button(toolbar, text="关闭", command=self._close_code_editor).grid(
            row=0, column=5, padx=(2, 0))

        self._create_statement_bar()
        self._create_editor_area()

    def _create_statement_bar(self) -> None:
        self._statement_bar = ttk.Frame(self._code_editor_frame, width=180,
                                        style='Editor.TFrame')
        self._statement_bar.grid(row=1, column=0, sticky="nsew")
        self._statement_bar.grid_rowconfigure(0, weight=0)
        self._statement_bar.grid_rowconfigure(1, weight=1)
        self._statement_bar.grid_propagate(False)

        ttk.Label(self._statement_bar, text="📋 操作面板", style='Editor.TLabel').grid(
            row=0, column=0, sticky="nw", padx=8, pady=(8, 2))

        self._statement_tree = ttk.Treeview(self._statement_bar, show="tree",
                                            selectmode='browse',
                                            style='Statement.Treeview')
        self._statement_tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 8))
        self._statement_bar.grid_columnconfigure(0, weight=1)

        # ── 分类语句体系 ──
        self._cat_statements = [
            ("🖱️ 鼠标操作", [
                ("移动鼠标到 (x, y)", "pyautogui.moveTo(x, y)"),
                ("移动鼠标到 (500, 300)", "pyautogui.moveTo(500, 300)"),
                ("单击鼠标左键", "pyautogui.click()"),
                ("双击鼠标左键", "pyautogui.doubleClick()"),
                ("单击鼠标右键", "pyautogui.click(button='right')"),
                ("鼠标左键按下", "pyautogui.mouseDown()"),
                ("鼠标左键释放", "pyautogui.mouseUp()"),
                ("鼠标滚轮向上滚", "pyautogui.scroll(10)"),
                ("鼠标滚轮向下滚", "pyautogui.scroll(-10)"),
                ("鼠标拖拽到 (x, y)", "pyautogui.drag(x, y, duration=0.5)"),
                ("获取当前鼠标坐标", "x, y = pyautogui.position()"),
            ]),
            ("⌨️ 键盘操作", [
                ("按下单个按键 (Enter)", "pyautogui.press('enter')"),
                ("输入文本内容", "pyautogui.typewrite('文本内容')"),
                ("逐字间隔输入文本", "pyautogui.typewrite('文本', interval=0.1)"),
                ("组合键 Ctrl+C", "pyautogui.hotkey('ctrl', 'c')"),
                ("组合键 Ctrl+V", "pyautogui.hotkey('ctrl', 'v')"),
                ("组合键 Alt+Tab", "pyautogui.hotkey('alt', 'tab')"),
                ("组合键 Win+R", "pyautogui.hotkey('win', 'r')"),
                ("按住按键不放", "pyautogui.keyDown('shift')"),
                ("释放按住按键", "pyautogui.keyUp('shift')"),
            ]),
            ("🖥️ 屏幕操作", [
                ("截取全屏保存", "pyautogui.screenshot('screenshot.png')"),
                ("截取指定区域", "pyautogui.screenshot('region.png', region=(0, 0, 300, 400))"),
                ("获取屏幕尺寸", "w, h = pyautogui.size()"),
                ("在屏幕查找图片位置", "pyautogui.locateOnScreen('target.png')"),
                ("获取图片中心坐标", "pyautogui.locateCenterOnScreen('target.png')"),
                ("获取像素颜色值", "pyautogui.pixel(x, y)"),
                ("判断像素颜色匹配", "pyautogui.pixelMatchesColor(x, y, (R, G, B))"),
            ]),
            ("💬 弹窗交互", [
                ("弹出信息提示框", "pyautogui.alert('提示内容')"),
                ("弹出确认对话框", "pyautogui.confirm('是否继续？')"),
                ("弹出文本输入框", "pyautogui.prompt('请输入：')"),
            ]),
            ("⏱️ 流程控制", [
                ("等待 0.5 秒", "time.sleep(0.5)"),
                ("等待 1 秒", "time.sleep(1)"),
                ("等待 2 秒", "time.sleep(2)"),
                ("等待 5 秒", "time.sleep(5)"),
                ("重复执行 3 次", "for i in range(3):"),
                ("条件判断分支", "if True:"),
            ]),
        ]

        # IID → code 映射
        self._stmt_code_map: Dict[str, str] = {}
        for cat_name, stmts in self._cat_statements:
            cat_iid = self._statement_tree.insert("", tk.END, text=cat_name,
                                                   open=True, tags=('category',))
            for display, code in stmts:
                child_iid = self._statement_tree.insert(
                    cat_iid, tk.END, text=display, tags=('statement',))
                self._stmt_code_map[child_iid] = code

        self._statement_tree.bind("<ButtonPress-1>", self._on_drag_start)
        self._statement_tree.bind("<B1-Motion>", self._on_drag)
        self._statement_tree.bind("<ButtonRelease-1>", self._on_drag_end)

        self._drag_clear_timer: str = ""

    def _create_editor_area(self) -> None:
        self._editor_frame = ttk.Frame(self._code_editor_frame, style='Editor.TFrame')
        self._editor_frame.grid(row=1, column=1, sticky="nsew")
        self._editor_frame.grid_rowconfigure(0, weight=0)
        self._editor_frame.grid_rowconfigure(1, weight=1)
        self._editor_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(self._editor_frame, text="操作编辑", style='Editor.TLabel').grid(
            row=0, column=0, sticky="nw", padx=10, pady=(8, 2))

        self._code_text = tk.Text(self._editor_frame,
                                  font=('Cascadia Code', 10),
                                  wrap=tk.WORD,
                                  bg=COLOR_BG_EDITOR,
                                  fg=COLOR_FG_EDITOR,
                                  insertbackground=COLOR_FG_EDITOR,
                                  selectbackground='#264f78',
                                  selectforeground='#ffffff',
                                  borderwidth=0,
                                  padx=10, pady=8,
                                  relief='flat')
        self._code_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))

        scrollbar = ttk.Scrollbar(self._editor_frame, orient=tk.VERTICAL,
                                  command=self._code_text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self._code_text.configure(yscrollcommand=scrollbar.set)

        self._code_text.bind("<ButtonRelease-1>", self._on_drop)

    def _on_drag_start(self, event: tk.Event) -> None:
        iid = self._statement_tree.identify_row(event.y)
        if iid and iid in self._stmt_code_map:
            self._drag_data.text = self._stmt_code_map[iid]
            self._statement_tree.selection_set(iid)
            self._statement_tree.focus(iid)
        else:
            self._drag_data.text = ""

    def _on_drag(self, event: tk.Event) -> None:
        pass

    def _on_drag_end(self, event: tk.Event) -> None:
        if self._drag_data.text:
            if self._drag_clear_timer:
                self.root.after_cancel(self._drag_clear_timer)
            self._drag_clear_timer = self.root.after(500, self._clear_drag_data)

    def _clear_drag_data(self) -> None:
        self._drag_data.item = -1
        self._drag_data.text = ""
        for sel in self._statement_tree.selection():
            self._statement_tree.selection_remove(sel)

    def _on_drop(self, event: tk.Event) -> None:
        if self._drag_data.text:
            self._code_text.insert(tk.INSERT, self._drag_data.text + "\n")
            if self._drag_clear_timer:
                self.root.after_cancel(self._drag_clear_timer)
            self._clear_drag_data()

    def _setup_bindings(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Configure>", self._on_root_configure)

        self.root.bind("<Control-o>", lambda e: self.menu_bar._import_json())
        self.root.bind("<Control-O>", lambda e: self.menu_bar._import_json())
        self.root.bind("<Control-s>", lambda e: self.menu_bar._save_json())
        self.root.bind("<Control-S>", lambda e: self.menu_bar._save_json())
        self.root.bind("<Control-Shift-s>", lambda e: self.menu_bar._export_json())
        self.root.bind("<Control-Shift-S>", lambda e: self.menu_bar._export_json())
        self.root.bind("<Control-n>", lambda e: self.add_hotkey_dialog())
        self.root.bind("<Control-N>", lambda e: self.add_hotkey_dialog())
        self.root.bind("<Control-f>", lambda e: self.menu_bar._toggle_search())
        self.root.bind("<Control-F>", lambda e: self.menu_bar._toggle_search())

    def _on_root_configure(self, event: tk.Event) -> None:
        """防止编辑器模式下窗口因 Tkinter 内部事件意外缩回窄模式。"""
        if not self._has_editor:
            return
        if event.widget is not self.root:
            return
        # 仅当宽度意外退回到窄模式附近时才自动恢复
        if event.width < self._original_width + 50:
            expected = self._original_width + self._editor_width
            self.root.after_idle(lambda: self.root.geometry(
                f"{expected}x{DEFAULT_WINDOW_HEIGHT}"))

    def open_code_editor(self, index: int) -> None:
        if index < 0 or index >= len(self.hotkey_tree.get_hotkeys()):
            return

        self._current_editing_index = index
        hotkey = self.hotkey_tree.get_hotkeys()[index]
        self._has_editor = True

        new_width = self._original_width + self._editor_width
        self.root.geometry(f"{new_width}x{DEFAULT_WINDOW_HEIGHT}")
        self.root.resizable(True, True)
        self._code_editor_frame.grid(row=0, column=1, sticky="nsew")

        code = '\n'.join(hotkey.get('code', []))
        self._code_text.delete(1.0, tk.END)
        self._code_text.insert(tk.END, code)

    def _save_code(self) -> None:
        if self._current_editing_index < 0:
            return

        code = self._code_text.get(1.0, tk.END).strip()
        code_lines = [line for line in code.split('\n') if line.strip()] if code else []

        if code_lines:
            warnings = HotKeyActuator.validate_code(code_lines)
            if warnings:
                warning_msg = ("代码包含潜在风险:\n\n" +
                               "\n".join(warnings) + "\n\n是否仍要保存？")
                if not messagebox.askyesno("安全警告", warning_msg):
                    return

        hotkeys = self.hotkey_tree.get_hotkeys()
        hotkeys[self._current_editing_index]['code'] = code_lines
        self.hotkey_tree.load_hotkeys(hotkeys)
        messagebox.showinfo("保存成功", "代码已保存")

    def _close_code_editor(self) -> None:
        if self._code_editor_frame:
            self._code_editor_frame.grid_remove()
            self._has_editor = False
            self._current_editing_index = -1
            self.root.geometry(f"{self._original_width}x{DEFAULT_WINDOW_HEIGHT}")
            self.root.resizable(False, False)

    def _capture_coordinate(self) -> None:
        """倒计时 3 秒后捕获鼠标坐标插入编辑器。"""
        self._start_countdown_capture(mode='coordinate')

    def _capture_color(self) -> None:
        """倒计时 3 秒后捕获鼠标位置像素颜色插入编辑器。"""
        self._start_countdown_capture(mode='color')

    def _start_countdown_capture(self, mode: str) -> None:
        """显示倒计时浮窗，结束后执行捕获。"""
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes('-topmost', True)
        overlay.configure(bg='#1e2733')

        label = tk.Label(overlay, text='3', font=('Microsoft YaHei UI', 36, 'bold'),
                         fg='#ffffff', bg='#1e2733', width=4, height=2)
        label.pack(padx=2, pady=2)

        # 居中放置
        overlay.update_idletasks()
        sw = overlay.winfo_screenwidth()
        sh = overlay.winfo_screenheight()
        w = overlay.winfo_width()
        h = overlay.winfo_height()
        overlay.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

        def tick(remaining: int) -> None:
            if remaining <= 0:
                overlay.destroy()
                self._do_capture(mode)
                return
            label.config(text=str(remaining))
            overlay.after(1000, tick, remaining - 1)

        overlay.after(200, tick, 2)  # 先显示 3，200ms 后开始递减
        overlay.grab_set()

    def _do_capture(self, mode: str) -> None:
        """执行实际捕获操作。"""
        try:
            import pyautogui
            if mode == 'coordinate':
                x, y = pyautogui.position()
                self._code_text.insert(tk.INSERT, f"{x}, {y}")
            elif mode == 'color':
                x, y = pyautogui.position()
                r, g, b = pyautogui.pixel(x, y)
                self._code_text.insert(tk.INSERT, f"({r}, {g}, {b})")
        except ImportError:
            messagebox.showerror("缺少依赖", "请先安装: pip install pyautogui")

    def _insert_screen_size(self) -> None:
        """插入当前屏幕尺寸。"""
        try:
            import pyautogui
            w, h = pyautogui.size()
            self._code_text.insert(tk.INSERT, str(w) + ", " + str(h))
        except ImportError:
            self._code_text.insert(tk.INSERT, "1920, 1080")

    def add_hotkey_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("添加热键")
        dialog.geometry("350x180")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        current_key = [""]
        is_listening = [False]

        key_frame = ttk.Frame(dialog, padding=10)
        key_frame.pack(fill="x", padx=5)
        ttk.Label(key_frame, text="热键:").grid(row=0, column=0, sticky="w", padx=5)
        key_entry = ttk.Entry(key_frame, width=25)
        key_entry.insert(0, "点击此处设置按键")
        key_entry.grid(row=0, column=1, sticky="ew", padx=5)

        desc_frame = ttk.Frame(dialog, padding=10)
        desc_frame.pack(fill="x", padx=5)
        ttk.Label(desc_frame, text="描述:").grid(row=0, column=0, sticky="w", padx=5)
        desc_entry = ttk.Entry(desc_frame, width=35)
        desc_entry.grid(row=0, column=1, sticky="ew", padx=5)
        desc_frame.grid_columnconfigure(1, weight=1)

        from hotkey.config import KEY_NAME_MAP, MODIFIER_MASKS, MODIFIER_KEYSYMS

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
            current_key[0] = key_str
            return "break"

        def on_focus_in(event: tk.Event) -> None:
            is_listening[0] = True
            key_entry.delete(0, tk.END)
            key_entry.insert(0, "现在按下按键...")

        def on_focus_out(event: tk.Event) -> None:
            is_listening[0] = False
            if not current_key[0]:
                key_entry.delete(0, tk.END)
                key_entry.insert(0, "点击此处设置按键")

        key_entry.bind('<FocusIn>', on_focus_in)
        key_entry.bind('<FocusOut>', on_focus_out)
        dialog.bind_class('Toplevel', '<KeyPress>', on_key_press, add='+')

        def cleanup() -> None:
            try:
                dialog.unbind_class('Toplevel', '<KeyPress>')
            except Exception:
                pass

        def confirm() -> None:
            key = current_key[0].strip()
            desc = desc_entry.get().strip()
            if not key or key in ["点击此处设置按键", "现在按下按键..."]:
                messagebox.showwarning("提示", "请点击热键框后按下热键", parent=dialog)
                return

            new_hotkey = {"key": key, "description": desc, "code": []}
            hotkeys = self.hotkey_tree.get_hotkeys()
            hotkeys.append(new_hotkey)
            self.hotkey_tree.load_hotkeys(hotkeys)
            cleanup()
            dialog.destroy()

        btn_frame = ttk.Frame(dialog, padding=10)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="确定", command=confirm).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="取消",
                   command=lambda: [cleanup(), dialog.destroy()]).pack(
            side="right", padx=5)

        dialog.protocol("WM_DELETE_WINDOW", lambda: [cleanup(), dialog.destroy()])
        desc_entry.focus_set()

    def export_json_dialog(self) -> None:
        hotkeys = self.hotkey_tree.get_hotkeys()
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

    def start_hotkey_listening(self) -> None:
        hotkeys = self.hotkey_tree.get_hotkeys()
        if not hotkeys:
            messagebox.showwarning("提示", "请先导入或添加热键配置")
            return

        missing_libs = []
        if keyboard is None:
            missing_libs.append("keyboard")
        if pystray is None or Image is None:
            missing_libs.append("pystray 和 pillow")

        if missing_libs:
            messagebox.showerror(
                "缺少依赖",
                f"请先安装以下库: {', '.join(missing_libs)}\n"
                f"运行命令: pip install {' '.join(m.replace(' 和 ', ' ') for m in missing_libs)}"
            )
            return

        self.actuator.set_hotkeys(hotkeys)
        if self.actuator.start():
            messagebox.showinfo("启动成功",
                                "热键监听已启动\n程序将在系统托盘中运行")
        else:
            messagebox.showerror("启动失败", "无法启动热键监听")

    def start_single_hotkey(self, index: int) -> None:
        hotkeys = self.hotkey_tree.get_hotkeys()
        if index < 0 or index >= len(hotkeys):
            return

        single_hotkey = [hotkeys[index]]
        self.actuator.set_hotkeys(single_hotkey)
        if self.actuator.start():
            messagebox.showinfo("启动成功",
                                f"已启动热键: {hotkeys[index].get('key')}")
        else:
            messagebox.showerror("启动失败", "无法启动热键监听")

    def _on_close(self) -> None:
        if self._is_listening:
            result = messagebox.askyesno(
                "热键监听运行中",
                "热键监听正在运行中。\n\n"
                "选择 \"是\" 隐藏主窗口，继续托盘检测\n"
                "选择 \"否\" 关闭程序"
            )
            if result:
                self.root.withdraw()
                logger.info("主窗口已隐藏，热键监听继续在托盘运行")
                return

        logger.info("正在关闭程序...")
        self.actuator.stop()
        self.root.destroy()

    def run(self) -> None:
        """启动应用程序主循环。"""
        self.root.mainloop()
