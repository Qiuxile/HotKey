# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（onedir）。

构建:
    .\.venv\Scripts\pyinstaller.exe --noconfirm HotKey.spec

说明:
    - onedir 而非 onefile：启动更快，也更容易满足 PySide6 的 LGPL 可替换要求
    - Qt 平台插件由 PyInstaller 的 PySide6 hook 自动收集
    - theme.qss 必须随包分发，app._theme_path() 会从 _MEIPASS 下读取
"""

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('hotkey/ui/theme.qss', 'hotkey/ui'),
        ('hotkey/core/catalog.json', 'hotkey/core'),
        ('assets', 'assets'),
    ],
    hiddenimports=[
        # 编辑器运行时才 import 监听器，静态分析看不到
        'hotkey.listener',
        # 脚本通过受限命名空间动态导入这些模块，PyInstaller 静态分析看不到
        'pyautogui',
        'pymsgbox',
        'pytweening',
        'pyscreeze',
        'mouseinfo',
        'keyboard',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HotKey',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon='assets/hotkey.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='HotKey',
)
