"""配置读写、格式迁移与原子保存（不依赖 Qt）。"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Iterable

from hotkey.core.keymap import normalize_key
from hotkey.core.models import HotKey, new_id

SCHEMA_VERSION = 2
CONFIG_DIR_NAME = "HotKey"
FILE_NAME = "hotkeys.json"


class StorageError(Exception):
    """配置读取或写入失败。"""


def default_config_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / CONFIG_DIR_NAME


def _candidate_config_dirs() -> list[Path]:
    candidates: list[Path] = []
    override = os.environ.get("HOTKEY_HOME")
    if override:
        candidates.append(Path(override))
    candidates.extend(
        [
            default_config_dir(),
            Path.home() / ".hotkey",
            Path.cwd() / ".hotkey",
        ]
    )

    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def config_root() -> Path:
    """返回第一个真正可写的配置目录。

    某些受限环境（或启用了受控文件夹访问的 Windows）不允许写入
    ``%APPDATA%``，此时依次回退到用户目录、当前目录，保证程序仍能保存配置。
    """
    for candidate in _candidate_config_dirs():
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write-probe"
            probe.write_text("", encoding="utf-8")
            probe.unlink()
            return candidate
        except OSError:
            continue
    return default_config_dir()


def default_config_path() -> Path:
    return config_root() / FILE_NAME


def _coerce_script(entry: dict[str, Any]) -> tuple[str, bool]:
    """返回 (脚本, 是否来自 v1 的 code 行列表)。"""
    script = entry.get("script")
    if isinstance(script, str):
        return script, False

    code = entry.get("code")
    if isinstance(code, str):
        return code, True
    if isinstance(code, list):
        lines = [line for line in code if isinstance(line, str)]
        return "\n".join(lines), True
    return "", False


def parse_document(data: Any) -> tuple[list[HotKey], list[str]]:
    """把 JSON 数据解析为热键列表，同时返回给用户看的警告。"""
    warnings: list[str] = []

    if isinstance(data, list):
        entries: list[Any] = data
        version = 1
    elif isinstance(data, dict):
        entries = data.get("hotkeys", [])
        raw_version = data.get("version", SCHEMA_VERSION)
        try:
            version = int(raw_version)
        except (TypeError, ValueError):
            warnings.append(f"无法识别的配置版本 {raw_version!r}，按当前版本读取")
            version = SCHEMA_VERSION
        if not isinstance(entries, list):
            raise StorageError("配置中的 hotkeys 必须是数组")
    else:
        raise StorageError("配置根节点必须是数组或对象")

    if version < SCHEMA_VERSION:
        warnings.append(f"检测到 v{version} 配置，已自动迁移到 v{SCHEMA_VERSION}")

    hotkeys: list[HotKey] = []
    seen: dict[str, HotKey] = {}
    migrated = 0

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            warnings.append(f"第{index + 1}条不是对象，已跳过")
            continue

        raw_key = entry.get("key")
        if not isinstance(raw_key, str):
            warnings.append(f"第{index + 1}条缺少有效的 key，已跳过")
            continue
        key = normalize_key(raw_key)
        if not key:
            warnings.append(f"第{index + 1}条 key 为空，已跳过")
            continue

        description = entry.get("description", "")
        if not isinstance(description, str):
            description = str(description)

        script, from_v1 = _coerce_script(entry)
        migrated += int(from_v1)

        raw_id = entry.get("id")
        entry_id = raw_id if isinstance(raw_id, str) and raw_id else new_id()

        enabled = entry.get("enabled", True)
        if not isinstance(enabled, bool):
            enabled = True

        hotkey = HotKey(
            key=key,
            description=description,
            script=script,
            enabled=enabled,
            id=entry_id,
        )

        if key in seen:
            hotkey.enabled = False
            warnings.append(
                f"热键 {key} 重复，已保留第一条并把第{index + 1}条设为停用"
            )
        else:
            seen[key] = hotkey

        hotkeys.append(hotkey)

    if migrated:
        warnings.append(f"已把 {migrated} 条旧格式（按行）配置迁移为整段脚本")

    return hotkeys, warnings


def load_document(path: Path | None = None) -> tuple[list[HotKey], list[str]]:
    """读取配置文件；文件不存在时返回空列表（首次启动）。"""
    target = Path(path) if path is not None else default_config_path()
    if not target.exists():
        return [], []

    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise StorageError(f"无法读取配置文件: {target}") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StorageError(f"配置文件不是合法 JSON: {target}（第{exc.lineno}行）") from exc

    return parse_document(data)


def load(path: Path | None = None) -> list[HotKey]:
    return load_document(path)[0]


def save(path: Path, hotkeys: Iterable[HotKey]) -> None:
    """原子写入：先写 .tmp，再替换，并保留一份 .bak。"""
    target = Path(path)
    payload = {
        "version": SCHEMA_VERSION,
        "hotkeys": [hotkey.to_dict() for hotkey in hotkeys],
    }

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        if target.exists():
            backup = target.with_name(target.name + ".bak")
            try:
                shutil.copy2(target, backup)
            except OSError:
                pass

        os.replace(tmp, target)
    except OSError as exc:
        raise StorageError(f"无法保存配置文件: {target}") from exc


def import_file(path: Path) -> tuple[list[HotKey], list[str]]:
    """从外部 JSON 导入，兼容 v1 / v2。"""
    return load_document(Path(path))


def export_file(path: Path, hotkeys: Iterable[HotKey]) -> None:
    save(Path(path), hotkeys)
