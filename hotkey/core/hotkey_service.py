"""全局热键注册服务（对 keyboard 库的封装）。"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Any

from hotkey.core.models import HotKey

logger = logging.getLogger("HotKey.HotkeyService")

try:
    import keyboard as _keyboard
except ImportError:  # pragma: no cover - 缺少依赖时给出可读错误
    _keyboard = None


class HotkeyService:
    """注册/注销热键，按稳定 id 管理句柄。

    `backend` 参数仅用于测试，生产环境默认使用 keyboard 库。
    """

    def __init__(
        self,
        on_trigger: Callable[[str], None],
        on_error: Callable[[str, str], None] | None = None,
        backend: Any = None,
    ) -> None:
        self._on_trigger = on_trigger
        self._on_error = on_error
        self._backend = backend if backend is not None else _keyboard
        self._handles: dict[str, Any] = {}
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self, entries: Iterable[HotKey]) -> None:
        if self._backend is None:
            raise RuntimeError("缺少 keyboard 库，请先运行 pip install keyboard")
        if self._running:
            self.stop()

        for entry in entries:
            if not entry.enabled or not entry.script.strip():
                continue
            try:
                handle = self._backend.add_hotkey(
                    entry.key,
                    self._make_handler(entry.id),
                    suppress=False,
                )
            except Exception as exc:  # noqa: BLE001 - 单个热键失败不影响其余
                logger.exception("注册热键 %s 失败", entry.key)
                self._report_error(entry.key, str(exc))
                continue
            self._handles[entry.id] = handle

        self._running = True

    def stop(self) -> None:
        if self._backend is None:
            self._running = False
            return

        for hotkey_id, handle in list(self._handles.items()):
            try:
                self._backend.remove_hotkey(handle)
            except Exception:  # noqa: BLE001
                logger.exception("注销热键 %s 失败", hotkey_id)
        self._handles.clear()
        self._running = False

    def reload(self, entries: Iterable[HotKey]) -> None:
        was_running = self._running
        self.stop()
        if was_running:
            self.start(entries)

    def _make_handler(self, hotkey_id: str) -> Callable[[], None]:
        def handler() -> None:
            try:
                self._on_trigger(hotkey_id)
            except Exception:  # noqa: BLE001 - 钩子线程必须保持存活
                logger.exception("热键 %s 回调失败", hotkey_id)

        return handler

    def _report_error(self, key: str, message: str) -> None:
        if self._on_error is None:
            return
        try:
            self._on_error(key, message)
        except Exception:  # noqa: BLE001
            logger.exception("on_error 回调失败")
