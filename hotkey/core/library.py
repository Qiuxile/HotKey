"""脚本库：一个脚本 = 一个 JSON 文件，热键可选。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from hotkey.core import storage
from hotkey.core.models import HotKey

INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


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
        self._migrate_legacy()

        scripts: list[HotKey] = []
        seen_keys: dict[str, HotKey] = {}

        for path in sorted(self.directory.glob("*.json")):
            if path.name == "hotkeys.json":
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
        for path in self.directory.glob("*.json"):
            if path.name == "hotkeys.json":
                continue
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
        candidate = self.directory / f"{stem}.json"
        index = 2
        while candidate.exists():
            candidate = self.directory / f"{stem}-{index}.json"
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
