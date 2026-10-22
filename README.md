# HotKey — 热键自动化工具

拖拽式零代码热键配置工具，面向非编程用户：从左侧操作面板把语句拖进编辑器，绑定一组全局热键，按下就执行。基于 **PySide6**，界面用 **Qt Designer** 的 `.ui` 文件维护。

> 旧版 Tkinter 实现保留在 `legacy/`，可执行 `python main_tk.py` 对比；迁移计划见 [docs/PLAN-qt-migration.md](docs/PLAN-qt-migration.md)。

## 功能

- **热键管理**：新建 / 修改 / 删除 / 启用停用，重复组合键自动拦截
- **拖拽式编辑器**：36 条预置语句、5 个分类，拖入后自动处理缩进；支持循环与条件块
- **代码辅助**：Python 语法高亮、Tab / 回车自动缩进、对白名单模块的导入校验
- **辅助工具**：3 秒倒计时捕获鼠标坐标、像素颜色、屏幕尺寸
- **全局监听**：`keyboard` 注册全局热键，脚本在工作线程串行执行，不阻塞界面
- **系统托盘**：关闭窗口最小化到托盘，托盘菜单可启停监听或退出
- **配置持久化**：启动自动加载，改动 800ms 防抖自动保存，导入/导出 JSON
- **单实例**：重复启动会激活已有窗口，避免重复注册热键

## 环境要求

- Windows 10 / 11
- Python 3.10+
- 运行时依赖见 `requirements.txt`（`PySide6-Essentials`、`keyboard`、`pyautogui`）

## 安装与运行

```powershell
# 开发环境（含 pytest / pyinstaller）
pip install -r requirements-dev.txt

# 运行
python main.py

# 冒烟测试：启动后自动退出
python main.py --self-test
```

打包：

```powershell
pyinstaller --noconfirm HotKey.spec
# 产物：dist\HotKey\HotKey.exe（onedir）
```

## 使用流程

1. `Ctrl+N` 打开对话框，在热键框里按下组合键（如 `Ctrl+Shift+A`），填写描述
2. 双击列表条目打开右侧编辑器
3. 从「操作面板」拖语句到编辑器，按需修改坐标 / 文本
4. 点「保存」，脚本会先经过安全校验
5. `F5` 启动监听；标题栏和托盘提示「监听中」
6. 关闭窗口会最小化到托盘；托盘右键「退出」才是真正退出

## 配置文件

默认位置：`%APPDATA%\HotKey\hotkeys.json`

如果该目录不可写（受限环境、受控文件夹访问等），会依次回退到 `~/.hotkey/hotkeys.json`、`.hotkey/hotkeys.json`，日志在配置目录下的 `logs/hotkey.log`。

v2 格式：

```json
{
  "version": 2,
  "hotkeys": [
    {
      "id": "3f2c9a...",
      "key": "ctrl+shift+a",
      "description": "弹出提示",
      "script": "pyautogui.alert('Hello')",
      "enabled": true
    }
  ]
}
```

也兼容旧版（v1）数组格式，导入时会把 `code` 行列表合并成整段 `script`。

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+N` | 新建热键 |
| `Ctrl+O` | 导入配置 |
| `Ctrl+Shift+S` | 导出配置 |
| `Ctrl+Q` | 退出程序 |
| `Ctrl+F` | 搜索 |
| `Ctrl+E` | 显示/隐藏操作编辑 |
| `F5` / `Shift+F5` | 启动 / 停止监听 |
| `Ctrl+Del` | 删除选中热键 |

## 脚本安全

保存前会对整段脚本做 AST 校验，执行前再校验一次：

- 允许：`pyautogui`、`time`、`datetime`、`math`、`random`、`json`、`re` 以及常用内置函数
- 禁止：`os` / `subprocess` 等模块，`eval` / `exec` / `open` / `__import__` 等调用，`__class__` 等 dunder 属性
- `import` 语句受白名单限制，执行命名空间只注入白名单模块

这是一道防误用的护栏，不是对抗恶意代码的安全边界——用户本来就能修改脚本。

## 项目结构

```
HotKey/
├── main.py                  # 入口（--self-test）
├── main_tk.py               # 旧版 Tk 入口
├── HotKey.spec              # PyInstaller onedir 配置
├── hotkey/
│   ├── app.py               # 启动、日志、单实例
│   ├── core/                # 不依赖 Qt，可独立测试
│   │   ├── models.py        # HotKey / Issue
│   │   ├── storage.py       # v1/v2 迁移、原子写、目录回退
│   │   ├── validator.py     # 整段 AST 校验 + 执行命名空间
│   │   ├── keymap.py        # Qt 键名 <-> keyboard 键名
│   │   ├── catalog.py       # 36 条语句目录
│   │   ├── hotkey_service.py# 热键注册
│   │   └── runner.py        # 单 worker 执行队列
│   └── ui/
│       ├── forms/           # Designer 源文件（main_window / hotkey_dialog）
│       ├── generated/       # pyside6-uic 生成物（提交入库）
│       ├── widgets/         # ScriptEditor / StatementTree / 高亮
│       ├── main_window.py
│       ├── hotkey_model.py
│       ├── recorder.py
│       └── theme.qss
├── tests/                   # pytest + pytest-qt（80 项）
├── tools/build_ui.ps1       # .ui -> generated/ui_*.py
└── legacy/                  # 旧 Tk 实现（仅参考）
```

## 开发

修改界面：用 Qt Designer 打开 `hotkey/ui/forms/*.ui`，保存后重新生成：

```powershell
.\.venv\Scripts\pyside6-designer.exe hotkey\ui\forms\main_window.ui
powershell -ExecutionPolicy Bypass -File tools\build_ui.ps1
```

生成物需要提交；`pytest` 里有一项会用 `build_ui.ps1 -Check` 检查 `.ui` 与生成物是否同步。

测试（无需真实桌面，Qt 使用 offscreen）：

```powershell
pytest
```

## 已知限制

- `keyboard` 库在部分 Windows 环境下需要以管理员身份运行才能收到全局按键
- 录制 `Win+X` 组合键时，系统可能同时响应（例如 `Win+R` 会打开「运行」）
- 脚本串行执行，长脚本会排队；`time.sleep` 不影响界面和热键注册，但会推迟后续脚本
- 打包产物是 onedir，不是单文件
