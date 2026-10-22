"""热键注册服务的单元测试（使用假 backend，不会真的挂全局钩子）。"""

from hotkey.core.hotkey_service import HotkeyService
from hotkey.core.models import HotKey


class FakeBackend:
    def __init__(self, fail_keys=()):
        self.added = []
        self.removed = []
        self.fail_keys = set(fail_keys)

    def add_hotkey(self, key, callback, suppress=False):
        if key in self.fail_keys:
            raise ValueError(f"bad key: {key}")
        handle = (key, callback)
        self.added.append(handle)
        return handle

    def remove_hotkey(self, handle):
        self.removed.append(handle)


def test_start_registers_only_enabled_scripts():
    backend = FakeBackend()
    triggered = []
    service = HotkeyService(triggered.append, backend=backend)

    entries = [
        HotKey(key="f1", script="x = 1", id="one"),
        HotKey(key="f2", script="", id="two"),
        HotKey(key="f3", script="x = 1", enabled=False, id="three"),
    ]
    service.start(entries)

    assert [key for key, _ in backend.added] == ["f1"]
    assert service.running is True

    backend.added[0][1]()
    assert triggered == ["one"]


def test_stop_removes_handles():
    backend = FakeBackend()
    service = HotkeyService(lambda _: None, backend=backend)
    service.start([HotKey(key="f1", script="x = 1")])
    service.stop()

    assert service.running is False
    assert len(backend.removed) == 1


def test_reload_only_when_running():
    backend = FakeBackend()
    service = HotkeyService(lambda _: None, backend=backend)

    service.reload([HotKey(key="f1", script="x = 1")])
    assert backend.added == []

    service.start([HotKey(key="f1", script="x = 1")])
    service.reload([HotKey(key="f2", script="x = 1")])
    assert [key for key, _ in backend.added] == ["f1", "f2"]
    assert len(backend.removed) == 1


def test_registration_error_is_reported_and_others_continue():
    backend = FakeBackend(fail_keys={"badkey"})
    errors = []
    service = HotkeyService(
        lambda _: None,
        on_error=lambda key, message: errors.append((key, message)),
        backend=backend,
    )

    service.start(
        [
            HotKey(key="badkey", script="x = 1"),
            HotKey(key="f1", script="x = 1"),
        ]
    )

    assert errors and errors[0][0] == "badkey"
    assert [key for key, _ in backend.added] == ["f1"]
