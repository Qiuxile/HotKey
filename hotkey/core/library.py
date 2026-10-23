"""脚本库：一个脚本 = 一个 JSON 文件，热键可选。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from hotkey.core import storage
from hotkey.core.models import HotKey

INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
SCRIPT_SUFFIX = ".hk"
LEGACY_SUFFIX = ".json"
SCRIPT_DIR_NAME = "hks"
LEGACY_DIR_NAME = "jsons"
HIDDEN_FILE = ".hidden.json"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _migrate_script_dir(base: Path) -> None:
    """旧版本用 jsons/；新版本用 hks/，首次启动时整体改名。"""
    old = base / LEGACY_DIR_NAME
    new = base / SCRIPT_DIR_NAME
    if new.exists() or not old.is_dir():
        return
    try:
        old.rename(new)
        return
    except OSError:
        pass
    try:
        new.mkdir(parents=True, exist_ok=True)
        for child in old.iterdir():
            child.replace(new / child.name)
    except OSError:
        pass


def default_script_dir() -> Path:
    """优先程序旁边的 hks/，不可写时回退到配置目录。"""
    root = app_root()
    _migrate_script_dir(root)
    config_root = storage.config_root()
    _migrate_script_dir(config_root)
    candidates = [
        root / SCRIPT_DIR_NAME,
        config_root / SCRIPT_DIR_NAME,
    ]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write-probe"
            probe.write_text("", encoding="utf-8")
            probe.unlink()
            return candidate
        except OSError:
            continue
    return candidates[0]


def safe_stem(name: str) -> str:
    cleaned = INVALID_NAME.sub("_", name).strip().strip(".")
    return cleaned or "脚本"


class ScriptLibrary:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        self.warnings: list[str] = []

    # ---------------------------------------------------------------- 读取

    def load(self, include_hidden: bool = False) -> list[HotKey]:
        self.warnings = []
        self.directory.mkdir(parents=True, exist_ok=True)
        self._migrate_extensions()
        self._migrate_legacy()

        scripts: list[HotKey] = []
        seen_keys: dict[str, HotKey] = {}
        hidden = self._read_hidden()

        for path in self._script_paths():
            if path.name in hidden and not include_hidden:
                continue
            try:
                entries, warnings = storage.load_document(
                    path, allow_empty_key=True
                )
            except storage.StorageError as exc:
                self.warnings.append(f"{path.name}: {exc}")
                continue

            self.warnings.extend(f"{path.name}: {w}" for w in warnings if w)
            if not entries:
                continue
            if len(entries) > 1:
                self.warnings.append(
                    f"{path.name}: 一个文件里有 {len(entries)} 个脚本，只载入第一个"
                )

            script = entries[0]
            script.path = path
            script.name = path.stem
            script.hidden = path.name in hidden

            if script.key:
                if script.key in seen_keys:
                    script.enabled = False
                    self.warnings.append(
                        f"{path.name}: 热键 {script.key} 与 "
                        f"{seen_keys[script.key].name} 重复，已停用"
                    )
                else:
                    seen_keys[script.key] = script

            scripts.append(script)

        scripts.sort(key=lambda script: script.name.lower())
        return scripts

    def _script_paths(self) -> list[Path]:
        paths = [
            path
            for path in self.directory.glob(f"*{SCRIPT_SUFFIX}")
            if path.is_file()
        ]
        # 兼容改名失败或手工放进来的旧 .json 脚本；hotkeys.json 是旧配置
        paths.extend(
            path
            for path in self.directory.glob(f"*{LEGACY_SUFFIX}")
            if path.is_file()
            and path.name not in ("hotkeys.json", HIDDEN_FILE)
        )
        return sorted(paths)

    def _migrate_extensions(self) -> None:
        renamed = 0
        for path in sorted(self.directory.glob(f"*{LEGACY_SUFFIX}")):
            if path.name in ("hotkeys.json", HIDDEN_FILE):
                continue
            target = path.with_suffix(SCRIPT_SUFFIX)
            if target.exists():
                continue
            try:
                path.replace(target)
                renamed += 1
            except OSError:
                continue
        if renamed:
            self.warnings.append(
                f"已把 {renamed} 个脚本从 .json 改名为 {SCRIPT_SUFFIX}"
            )

    def _migrate_legacy(self) -> None:
        candidates = [self.directory / "hotkeys.json"]
        try:
            if self.directory.resolve() == default_script_dir().resolve():
                candidates.append(storage.config_root() / "hotkeys.json")
        except OSError:
            pass

        legacy = next((path for path in candidates if path.exists()), None)
        if legacy is None:
            return

        existing_ids: set[str] = set()
        for path in self._script_paths():
            try:
                entries, _warnings = storage.load_document(
                    path, allow_empty_key=True
                )
            except storage.StorageError:
                continue
            existing_ids.update(script.id for script in entries)

        try:
            entries, _warnings = storage.load_document(legacy)
        except storage.StorageError as exc:
            self.warnings.append(f"{legacy.name}: {exc}")
            return

        migrated = 0
        for script in entries:
            if script.id in existing_ids:
                continue
            script.name = safe_stem(
                script.description or script.key or "脚本"
            )
            try:
                self.save(script, unique=True)
                migrated += 1
            except storage.StorageError as exc:
                self.warnings.append(f"{script.name}: {exc}")

        try:
            legacy.replace(legacy.with_name(legacy.name + ".migrated"))
        except OSError:
            pass

        if migrated:
            self.warnings.append(
                f"已把 {migrated} 个热键从 {legacy.name} 拆成单脚本文件"
            )

    # ---------------------------------------------------------------- 写入

    def unique_path(self, name: str) -> Path:
        stem = safe_stem(name)
        candidate = self.directory / f"{stem}{SCRIPT_SUFFIX}"
        index = 2
        while candidate.exists():
            candidate = self.directory / f"{stem}-{index}{SCRIPT_SUFFIX}"
            index += 1
        return candidate

    def path_for(self, script: HotKey) -> Path:
        if script.path is not None:
            return script.path
        target = self.unique_path(script.name or script.description or "脚本")
        script.path = target
        script.name = target.stem
        return target

    def save(self, script: HotKey, unique: bool = False) -> Path:
        if unique or script.path is None:
            if unique:
                script.path = self.unique_path(script.name or "脚本")
            target = self.path_for(script)
        else:
            target = script.path
        storage.save(target, [script])
        return target

    def _hidden_path(self) -> Path:
        return self.directory / HIDDEN_FILE

    def _read_hidden(self) -> set[str]:
        path = self._hidden_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return set()
        if not isinstance(data, list):
            return set()
        return {str(name) for name in data if isinstance(name, str)}

    def _write_hidden(self, names: set[str]) -> None:
        path = self._hidden_path()
        path.write_text(
            json.dumps(sorted(names), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def hide(self, script: HotKey) -> None:
        """只在列表中隐藏；文件、内容和位置都不变。"""
        if script.path is None:
            return
        names = self._read_hidden()
        names.add(script.path.name)
        self._write_hidden(names)
        script.hidden = True

    def unhide(self, script: HotKey) -> None:
        if script.path is None:
            return
        names = self._read_hidden()
        names.discard(script.path.name)
        self._write_hidden(names)
        script.hidden = False

    def remove(self, script: HotKey) -> None:
        """旧名称，保留给已有调用；现在等同于隐藏。"""
        self.hide(script)

    def delete(self, script: HotKey) -> None:
        if script.path is None:
            return
        for path in (
            script.path,
            script.path.with_name(script.path.name + ".bak"),
        ):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    def import_copy(self, source: Path) -> HotKey:
        entries, _warnings = storage.load_document(source, allow_empty_key=True)
        if not entries:
            raise storage.StorageError("文件里没有脚本")
        script = entries[0]
        script.name = safe_stem(source.stem)
        script.path = self.unique_path(script.name)
        storage.save(script.path, [script])
        return script