"""执行队列的单元测试（不依赖真实 GUI / pyautogui）。"""

import threading
import time

from hotkey.core.runner import ScriptRunner


def collect_finished():
    results = []
    done = threading.Event()

    def on_finished(hotkey_id, ok, message):
        results.append((hotkey_id, ok, message))
        done.set()

    return results, done, on_finished


def wait_for(done, timeout=5.0):
    assert done.wait(timeout), "runner 未在预期时间内完成"


def test_runner_executes_script():
    results, done, on_finished = collect_finished()
    runner = ScriptRunner(on_finished=on_finished)
    try:
        assert runner.submit("abc", "x = 1") is True
        wait_for(done)
    finally:
        runner.shutdown()

    assert results == [("abc", True, "")]


def test_runner_reports_runtime_error():
    results, done, on_finished = collect_finished()
    runner = ScriptRunner(on_finished=on_finished)
    try:
        runner.submit("abc", "1 / 0")
        wait_for(done)
    finally:
        runner.shutdown()

    hotkey_id, ok, message = results[0]
    assert hotkey_id == "abc"
    assert ok is False
    assert "division by zero" in message


def test_runner_rejects_forbidden_script():
    results, done, on_finished = collect_finished()
    runner = ScriptRunner(on_finished=on_finished)
    try:
        runner.submit("abc", "import os")
        wait_for(done)
    finally:
        runner.shutdown()

    hotkey_id, ok, message = results[0]
    assert ok is False
    assert "os" in message


def test_runner_serializes_jobs():
    order = []
    done = threading.Event()

    def executor(script):
        order.append(script)
        time.sleep(0.05)

    def on_finished(hotkey_id, ok, message):
        if len(order) == 3:
            done.set()

    runner = ScriptRunner(executor=executor, on_finished=on_finished)
    try:
        for index in range(3):
            runner.submit(str(index), f"x = {index}")
        wait_for(done)
    finally:
        runner.shutdown()

    assert order == ["x = 0", "x = 1", "x = 2"]
