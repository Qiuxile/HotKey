"""脚本执行队列：单个 worker 线程串行执行，绝不占用键盘钩子线程。"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable

from hotkey.core import validator
from hotkey.core.models import IssueLevel

logger = logging.getLogger("HotKey.Runner")

DEFAULT_MAX_QUEUE = 5


class ScriptError(Exception):
    """脚本被安全校验拒绝。"""


def execute_script(script: str) -> None:
    """校验并执行整段脚本（在 worker 线程中调用）。"""
    issues = validator.validate(script)
    errors = [issue for issue in issues if issue.level is IssueLevel.ERROR]
    if errors:
        raise ScriptError("；".join(str(issue) for issue in errors))

    code = validator.compile_script(script)
    exec(code, validator.build_namespace())


class ScriptRunner:
    """单线程执行器。

    `on_started` / `on_finished` 会在 worker 线程里被调用，界面层需要自行
    通过信号切换到主线程。
    """

    def __init__(
        self,
        executor: Callable[[str], None] = execute_script,
        on_started: Callable[[str], None] | None = None,
        on_finished: Callable[[str, bool, str], None] | None = None,
        max_queue: int = DEFAULT_MAX_QUEUE,
    ) -> None:
        self._executor = executor
        self._on_started = on_started
        self._on_finished = on_finished
        self._queue: queue.Queue[tuple[str, str] | None] = queue.Queue(
            maxsize=max_queue
        )
        self._thread = threading.Thread(
            target=self._run,
            name="hotkey-script-runner",
            daemon=True,
        )

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def submit(self, hotkey_id: str, script: str) -> bool:
        """入队执行；队列满时立刻回调失败。"""
        if not self._thread.is_alive():
            self.start()
        try:
            self._queue.put_nowait((hotkey_id, script))
        except queue.Full:
            self._notify_finished(hotkey_id, False, "执行队列已满，已跳过")
            return False
        return True

    def pending(self) -> int:
        return self._queue.qsize()

    def shutdown(self, wait_seconds: float = 2.0) -> None:
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread.is_alive():
            self._thread.join(wait_seconds)

    # ------------------------------------------------------------------ 内部

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    return
                hotkey_id, script = item
                self._notify_started(hotkey_id)
                try:
                    self._executor(script)
                except Exception as exc:  # noqa: BLE001 - 用户脚本错误必须被隔离
                    logger.exception("热键 %s 执行失败", hotkey_id)
                    self._notify_finished(hotkey_id, False, str(exc))
                else:
                    self._notify_finished(hotkey_id, True, "")
            finally:
                self._queue.task_done()

    def _notify_started(self, hotkey_id: str) -> None:
        if self._on_started is None:
            return
        try:
            self._on_started(hotkey_id)
        except Exception:  # noqa: BLE001 - 回调异常不能杀死 worker
            logger.exception("on_started 回调失败")

    def _notify_finished(self, hotkey_id: str, ok: bool, message: str) -> None:
        if self._on_finished is None:
            return
        try:
            self._on_finished(hotkey_id, ok, message)
        except Exception:  # noqa: BLE001
            logger.exception("on_finished 回调失败")
