"""热键执行器 - 负责监听和执行热键。"""

import logging
import queue
import threading
import tkinter as tk
from typing import List, Dict, Any, Optional, Callable, TYPE_CHECKING

from hotkey.code_executor import CodeExecutor

if TYPE_CHECKING:
    from hotkey.app import App

logger = logging.getLogger('HotKey.Actuator')

# 条件导入
try:
    import keyboard
except ImportError:
    keyboard = None

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None
    Image = None
    ImageDraw = None


class HotKeyActuator:
    """热键执行器，负责监听和执行热键。"""

    def __init__(self, master: Optional[tk.Widget] = None,
                 hotkeys_data: Optional[List[Dict[str, Any]]] = None,
                 app: Optional['App'] = None):
        self._master = master
        self._app = app
        self._hotkeys: List[Dict[str, Any]] = hotkeys_data or []
        self._running = False
        self._tray_icon: Optional[pystray.Icon] = None
        self._hotkey_handlers: Dict[str, Callable] = {}
        self._tray_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._gui_queue: queue.Queue = queue.Queue()
        self._code_executor = CodeExecutor()

    def set_hotkeys(self, hotkeys: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._hotkeys = hotkeys.copy()
        self._code_executor.clear_cache()

    @property
    def gui_queue(self) -> queue.Queue:
        return self._gui_queue

    def _execute_code(self, code_list: List[str]) -> None:
        self._code_executor.execute(code_list)

    @staticmethod
    def validate_code(code_list: List[str]) -> List[str]:
        return CodeExecutor.validate(code_list)

    def _create_tray_image(self) -> Image.Image:
        width, height = 64, 64
        image = Image.new('RGB', (width, height), color='white')
        dc = ImageDraw.Draw(image)
        dc.rectangle([10, 10, 54, 54], outline='black', width=2)
        dc.text((20, 25), 'HK', fill='black')
        return image

    def _on_tray_click(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        item_str = str(item)
        if item_str == '退出':
            self.stop()
            icon.stop()
        elif item_str == '显示主窗口' and self._master:
            self._gui_queue.put(lambda: self._master.deiconify())
            self._gui_queue.put(lambda: self._master.lift())
            self._gui_queue.put(lambda: self._master.focus_set())
        elif item_str == '隐藏主窗口' and self._master:
            self._gui_queue.put(lambda: self._master.withdraw())

    def _create_tray_menu(self) -> pystray.Menu:
        if self._master:
            return pystray.Menu(
                pystray.MenuItem('显示主窗口', self._on_tray_click),
                pystray.MenuItem('隐藏主窗口', self._on_tray_click),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('退出', self._on_tray_click)
            )
        return pystray.Menu(
            pystray.MenuItem('退出', self._on_tray_click)
        )

    def _setup_tray(self) -> None:
        if not pystray or not Image:
            return
        try:
            image = self._create_tray_image()
            menu = self._create_tray_menu()
            self._tray_icon = pystray.Icon("HotKey", image, "热键执行器", menu)
            self._tray_icon.run()
        except Exception as e:
            logger.error("系统托盘启动失败: %s", e, exc_info=True)

    def _start_tray(self) -> None:
        if not pystray or not Image:
            return
        try:
            self._tray_thread = threading.Thread(target=self._setup_tray, daemon=True)
            self._tray_thread.start()
        except Exception as e:
            logger.error("托盘线程启动失败: %s", e, exc_info=True)

    def _register_hotkeys(self) -> None:
        if not keyboard:
            return
        # 检测重复 key
        seen_keys: Dict[str, int] = {}
        with self._lock:
            unique_hotkeys = []
            for hk in self._hotkeys:
                key_str = hk.get('key', '').lower()
                if not key_str:
                    continue
                if key_str in seen_keys:
                    logger.warning("重复热键 '%s'，跳过后续条目", key_str)
                    continue
                seen_keys[key_str] = 1
                unique_hotkeys.append(hk)
            self._hotkeys = unique_hotkeys

        for hotkey in self._hotkeys:
            key_str = hotkey.get('key', '').lower()
            code_list = hotkey.get('code', [])
            if not key_str:
                continue
            try:
                handler = lambda c=code_list: self._execute_code(c)
                keyboard.add_hotkey(key_str, handler)
                with self._lock:
                    self._hotkey_handlers[key_str] = handler
            except Exception as e:
                logger.error("注册热键 '%s' 失败: %s", key_str, e, exc_info=True)

    def _unregister_hotkeys(self) -> None:
        if not keyboard:
            return
        try:
            with self._lock:
                keys_to_remove = list(self._hotkey_handlers.keys())
            for key_str in keys_to_remove:
                try:
                    keyboard.remove_hotkey(key_str)
                except Exception as e:
                    logger.error("注销热键 '%s' 失败: %s", key_str, e, exc_info=True)
            with self._lock:
                self._hotkey_handlers.clear()
        except Exception as e:
            logger.error("注销热键列表失败: %s", e, exc_info=True)

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return False
            if not self._hotkeys:
                return False

        try:
            with self._lock:
                self._running = True
            self._register_hotkeys()
            self._start_tray()
            if self._app:
                self._app.is_listening = True
            return True
        except Exception as e:
            with self._lock:
                self._running = False
            logger.error("启动热键监听失败: %s", e, exc_info=True)
            return False

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False

        self._unregister_hotkeys()

        if self._app:
            self._app.is_listening = False

        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception as e:
                logger.error("托盘图标停止失败: %s", e, exc_info=True)
