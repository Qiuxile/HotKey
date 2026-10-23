"""脚本库：一个 .hk 文件可以包含多个热键，每个热键有自己的积木。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from hotkey.core import storage
from hotkey.core.models import HotKey, new_id

INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
SCRIPT_SUFFIX = ".hk"
LEGACY_SUFFIX = ".json"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def default_script_dir() -> Path:
    """优先程序旁边的 jsons/，不可写时回退到配置目录。"""
    candidates = [
        app_root() / "jsons",
        storage.config_root() / "jsons",
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

    def load(self) -> list[HotKey]:
        self.warnings = []
        self.directory.mkdir(parents=True, exist_ok=True)
        self._migrate_extensions()
        self._migrate_legacy()

        scripts: list[HotKey] = []
        seen_keys: dict[str, HotKey] = {}

        for path in self._script_paths():
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

            for index, script in enumerate(entries):
                script.path = path
                if len(entries) == 1:
                    script.name = path.stem
                elif script.description.strip():
                    script.name = script.description.strip()
                else:
                    script.name = f"{path.stem} #{index + 1}"

                if script.key:
                    if script.key in seen_keys:
                        script.enabled = False
                        self.warnings.append(
                            f"{script.name}: 热键 {script.key} 与 "
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
            if path.is_file() and path.name != "hotkeys.json"
        )
        return sorted(paths)

    def _migrate_extensions(self) -> None:
        renamed = 0
        for path in sorted(self.directory.glob(f"*{LEGACY_SUFFIX}")):
            if path.name == "hotkeys.json":
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

        entries: list[HotKey] = []
        if target.exists():
            try:
                existing, _warnings = storage.load_document(
                    target, allow_empty_key=True
                )
            except storage.StorageError:
                existing = []
            replaced = False
            for old in existing:
                if old.id == script.id:
                    entries.append(script)
                    replaced = True
                else:
                    entries.append(old)
            if not replaced:
                entries.append(script)
        else:
            entries.append(script)

        self.save_all(target, entries)
        return target

    def save_all(self, path: Path, scripts: list[HotKey]) -> None:
        for script in scripts:
            script.path = path
        storage.save(path, scripts)

    def delete(self, script: HotKey) -> None:
        if script.path is None:
            return
        path = script.path
        remaining: list[HotKey] = []
        try:
            entries, _warnings = storage.load_document(
                path, allow_empty_key=True
            )
            remaining = [entry for entry in entries if entry.id != script.id]
        except (storage.StorageError, FileNotFoundError):
            remaining = []

        if remaining:
            self.save_all(path, remaining)
            return

        for target in (path, path.with_name(path.name + ".bak")):
            try:
                target.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    def import_copy(self, source: Path) -> list[HotKey]:
        entries, _warnings = storage.load_document(source, allow_empty_key=True)
        if not entries:
            raise storage.StorageError("文件里没有热键")

        target = self.unique_path(source.stem)
        for index, entry in enumerate(entries):
            entry.id = new_id()
            if entry.description.strip():
                entry.name = entry.description.strip()
            elif len(entries) == 1:
                entry.name = source.stem
            else:
                entry.name = f"{source.stem} #{index + 1}"
        self.save_all(target, entries)
        return entries