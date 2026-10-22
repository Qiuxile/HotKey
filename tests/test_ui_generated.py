"""校验 pyside6-uic 生成物与 .ui 源文件保持同步。"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "build_ui.ps1"


def _powershell() -> str | None:
    for name in ("powershell", "pwsh"):
        found = shutil.which(name)
        if found:
            return found
    return None


def test_generated_ui_is_up_to_date():
    shell = _powershell()
    if shell is None:
        pytest.skip("未找到 PowerShell，跳过生成物校验")
    if not SCRIPT.exists():
        pytest.skip(f"缺少脚本: {SCRIPT}")

    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-Check",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0, result.stdout + result.stderr
