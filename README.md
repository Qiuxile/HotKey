# HotKey — 热键自动化工具

拖拽式零代码热键配置工具：把左侧的中文积木拖到右侧拼成脚本，绑定全局热键，按下就执行。基于 **PySide6**，界面用 **Qt Designer** 的 `.ui` 文件维护。

> 旧版 Tkinter 实现保留在 `legacy/`，可执行 `python main_tk.py` 对比；迁移计划见 [docs/PLAN-qt-migration.md](docs/PLAN-qt-migration.md)。

## 功能

- **积木式编辑**：右侧是积木列表，只能从左侧拖入，不能直接打字
- **中文优先**：拖入后显示这一行的中文，参数留空等用户填写
- **空格编辑**：点选积木后按空格编辑参数；删改内容不合法会自动还原
- **空积木**：左侧最顶上的「空」拖进来后可以自己写代码
- **嵌套流程**：把积木拖到「重复执行 / 条件判断」积木的中间，就成为它的子块
- **热键管理**：新建 / 修改 / 删除 / 启用停用，重复组合键自动拦截
- **全局监听**：`keyboard` 注册热键，脚本在独立 worker 线程串行执行，不阻塞界面
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
2. 双击列表条目打开右侧积木栏
3. 从左侧「操作面板」把中文积木拖到右侧
4. 选中积木按 **空格**，把中文里的参数补全（例如 `移动鼠标到（, ）` → `移动鼠标到（800, 600）`）
5. 需要循环/判断时，先拖入「重复执行 3 次」，再把其他积木拖到它中间
6. 点「保存」，积木会先被翻译成脚本并做安全校验
7. `F5` 启动监听；标题栏和托盘提示「监听中」
8. 关闭窗口会最小化到托盘；托盘右键「退出」才是真正退出

左侧最顶上的「空」是一块空白积木：拖入后按空格，可以写任意一行 Python 代码。

## 配置文件

默认位置：`%APPDATA%\HotKey\hotkeys.json`

如果该目录不可写（受限环境、受控文件夹访问等），会依次回退到 `~/.hotkey/hotkeys.json`、`.hotkey/hotkeys.json`，日志在配置目录下的 `logs/hotkey.log`。

v3 格式（同时保留 `script` 方便执行与旧版读取）：

```json
{
  "version": 3,
  "hotkeys": [
    {
      "id": "3f2c9a...",
      "key": "ctrl+shift+a",
      "description": "弹出提示",
      "enabled": true,
      "script": "pyautogui.alert('Hello')",
      "blocks": [
        { "kind": "dialog_alert", "text": "弹出提示：Hello", "children": [] }
      ]
    }
  ]
}
```

旧版（v1/v2）的脚本会自动迁移成一个「空」积木，仍然可以继续拖拽组合。

## 快捷键

| 位置 | 快捷键 | 功能 |
|------|--------|------|
| 主窗口 | `Ctrl+N` | 新建热键 |
| 主窗口 | `Ctrl+O` | 导入配置 |
| 主窗口 | `Ctrl+Shift+S` | 导出配置 |
| 主窗口 | `Ctrl+Q` | 退出程序 |
| 主窗口 | `Ctrl+F` | 搜索 |
| 主窗口 | `Ctrl+E` | 显示/隐藏操作编辑 |
| 主窗口 | `F5` / `Shift+F5` | 启动 / 停止监听 |
| 主窗口 | `Ctrl+Del` | 删除选中热键 |
| 积木栏 | `空格` | 编辑选中的积木 |
| 积木栏 | `Delete` | 删除选中的积木 |

## 脚本安全

积木会被翻译成整段 Python，在保存前和执行前各做一次 AST 校验：

- 允许：`pyautogui`、`time`、`datetime`、`math`、`random`、`json`、`re` 以及常用内置函数
- 禁止：`os` / `subprocess` 等模块，`eval` / `exec` / `open` / `__import__` 等调用，`__class__` 等 dunder 属性
- `import` 语句受白名单限制，执行命名空间只注入白名单模块

这是一道防误用的护栏，不是对抗恶意代码的安全边界——「空」积木本来就能写代码。

## 项目结构

```
HotKey/
├── main.py                  # 入口（--self-test）
├── main_tk.py               # 旧版 Tk 入口
├── HotKey.spec              # PyInstaller onedir 配置
├── hotkey/
│   ├── app.py               # 启动、日志、单实例
│   ├── core/                # 不依赖 Qt，可独立测试
│   │   ├── models.py        # HotKey / Block / Issue
│   │   ├── blocks.py        # 积木 -> Python 代码
│   │   ├── catalog.py       # 36 条积木：中文模板 + 代码模板
│   │   ├── storage.py       # v1/v2/v3 迁移、原子写、目录回退
│   │   ├── validator.py     # 整段 AST 校验 + 执行命名空间
│   │   ├── keymap.py        # Qt 键名 <-> keyboard 键名
│   │   ├── hotkey_service.py# 热键注册
│   │   └── runner.py        # 单 worker 执行队列
│   └── ui/
│       ├── forms/           # Designer 源文件（main_window / hotkey_dialog）
│       ├── generated/       # pyside6-uic 生成物（提交入库）
│       ├── widgets/         # BlockTree / StatementTree
│       ├── main_window.py
│       ├── hotkey_model.py
│       ├── recorder.py
│       └── theme.qss
├── tests/                   # pytest + pytest-qt（122 项）
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

新增/修改积木：编辑 `hotkey/core/catalog.py`，同时写中文 `label` 和 `code` 模板，参数用 `{name}` 占位；需要引号包裹的文本参数加进 `quoted`。

测试（无需真实桌面，Qt 使用 offscreen）：

```powershell
pytest
```

## 已知限制

- `keyboard` 库在部分 Windows 环境下需要以管理员身份运行才能收到全局按键
- 录制 `Win+X` 组合键时，系统可能同时响应（例如 `Win+R` 会打开「运行」）
- 积木参数靠中文模板正则解析：如果把中文标签本身改坏，会还原并提示，不会静默生成错代码
- 脚本串行执行，长脚本会排队；`time.sleep` 不影响界面和热键注册，但会推迟后续脚本
- 打包产物是 onedir，不是单文件
