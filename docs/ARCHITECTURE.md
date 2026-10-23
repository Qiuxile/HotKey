# 代码结构说明

这份文档给第一次读代码的人：先看这里，再按模块跳转。

## 1. 一句话模型

**一个脚本 = 一个 `.hk` 文件（JSON 内容）**。脚本包含积木、可选热键、启用状态。
热键只是运行脚本的一种方式；脚本也可以手动运行或导出成独立 `.py`。

代码里的 `HotKey` 是脚本对象的历史命名，不要把它只理解成"热键"。

## 2. 目录速查

```
hotkey/
├── core/                 # 不依赖 PySide6，可单独 pytest
│   ├── models.py         # HotKey（脚本）、Block（积木）、Issue
│   ├── blocks.py         # 积木树 -> Python 代码
│   ├── program.py        # 生成可独立运行的 .py
│   ├── library.py        # 单文件脚本库：加载/保存/删除/迁移
│   ├── storage.py        # 单文件内 JSON 的解析、v1~v5 迁移、原子写
│   ├── validator.py      # 保存/执行前的 AST 安全校验
│   ├── catalog.json      # 积木表：中文模板、参数、槽位、代码、分类颜色
│   ├── catalog.py        # 读取 catalog.json，渲染/解析积木
│   ├── keymap.py         # Qt 键名 <-> keyboard 键名
│   ├── hotkey_service.py # keyboard 全局热键注册
│   └── runner.py         # 单 worker 脚本执行队列
├── ui/
│   ├── forms/*.ui        # Qt Designer 源文件
│   ├── generated/        # pyside6-uic 生成物（提交入库，勿手改）
│   ├── main_window.py    # 编辑器：脚本库、编辑标签、试运行
│   ├── listener.py       # 独立监听器：托盘 + 热键 + 文件热重载
│   ├── hotkey_model.py   # 脚本列表的 QAbstractTableModel + 搜索代理
│   ├── recorder.py       # 热键录入对话框
│   ├── logging_setup.py  # 编辑器/监听器共用日志
│   ├── icon.py           # 共用应用图标
│   ├── theme.py          # 深/浅色调色板、QSS 渲染、QSettings
│   ├── theme.qss         # 使用 $变量 的 QSS 模板
│   └── widgets/
│       ├── block_editor.py     # 单栏积木编辑器（含拖拽排序）
│       ├── statement_tree.py   # 积木柜：分类 + 搜索 + 拖出积木
│       ├── title_bar.py        # 自定义标题栏 + 菜单按钮
│       └── frameless_resize.py # 无边框窗口四边/四角缩放
└── app.py                # 编辑器启动、单实例
```

## 3. 主窗口的职责分区

`ui/main_window.py` 按注释分成几块，读的时候可以按块看：

| 区块 | 关键方法 | 职责 |
|---|---|---|
| 外观 | `_setup_chrome`、`_init_theme`、`_toggle_theme` | 标题栏、菜单、主题 |
| 初始化 | `_configure_table`、`_connect_signals`、`_load_library` | 建模型、连信号、加载脚本库 |
| 脚本库 | `_new_script`、`_import_script`、`_delete_script`、`_edit_hotkey` | 脚本文件与列表操作 |
| 编辑标签 | `_open_editor_for_id`、`_activate_tab`、`_save_tab`、`_close_tab` | 多标签编辑与保存 |
| 运行/导出 | `_run_script`、`_export_python` | 试运行 / 生成 `.py` |
| 监听进程 | `_start_listening`、`_stop_listening`、`_verify_listener_start` | 启动/停止独立监听器进程 |
| 编辑器工具 | `_capture_coordinate`、`_insert_pixel_color` | 复制坐标/颜色/尺寸 |
| 窗口/退出 | `_update_window_title`、`closeEvent`、`_quit` | 标题、保存提示、退出 |

`MainWindow` 只做协调；积木代码生成、校验、文件格式、热键注册都在 `core/`。
窗口边缘缩放已拆到 `widgets/frameless_resize.py`，不要重新塞回主窗口。
编辑器**没有托盘**；托盘只属于 `hotkey/listener.py` 的监听器进程。

## 4. 数据流

```
jsons/*.hk
   │ ScriptLibrary.load()
   ▼
HotKey 列表 ──► HotKeyTableModel ──► 左侧列表
   │
   │ 双击 / 右键“编辑”
   ▼
EditorTab（右侧标签，内存中的 blocks）
   │ 拖积木 / 改参数
   ▼
blocks_to_code() ──► validator.validate() ──► library.save() 写回 .hk
   │
   ├── F5：启动独立监听器进程（监听器负责注册热键）
   └── 生成 .py：render_program() 生成独立文件
```

监听器进程：

```
jsons/*.hk ──ScriptLibrary.load()──► 有热键且启用的脚本
   │                                      │
   │ QFileSystemWatcher 监视 .hk           │ HotkeyService 注册
   ▼                                      ▼
保存后自动 reload ───────────────► 按键触发 ──► ScriptRunner 执行
   │
   └── 托盘：打开编辑器 / 暂停 / 退出
```

编辑器与监听器通过 `QLocalSocket`（`HotKey.Listener.v1`）通信：
启动、停止、查询状态；脚本内容通过文件同步。

关键不变量：

- 左侧列表保存**全部脚本**；右侧标签只表示**正在编辑**的脚本。
- 标签里的积木修改只在内存，点保存才写文件；`*` 表示有未保存修改。
- 没有热键（`key == ""`）的脚本不会注册全局热键，但仍可运行/导出。
- 不同脚本文件不能使用同一个热键；加载时会停用重复项。

## 5. 改哪里

### 加一个积木

只改 `core/catalog.json`：`id`、`category`、`label`、`code`、`params`、`slots`。
`label` 里的 `{name}` 会变成常驻输入框；不需要改 UI 代码。
加完跑 `pytest tests/test_catalog.py`。全部积木清单见 [BLOCKS.md](BLOCKS.md)。

### 改主窗口布局

改 `ui/forms/main_window.ui`，然后：

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_ui.ps1
```

生成物 `ui/generated/ui_main_window.py` 必须一起提交。

### 改主题

- 调色板：`ui/theme.py` 的 `PALETTES`
- 样式：`ui/theme.qss`，使用 `$bg`、`$text`、`$border` 等占位符
- 两处要同时改，否则 QSS 里会出现未替换的 `$变量`

### 加脚本字段

按顺序改：

1. `core/models.py` 的 `HotKey` 字段和 `to_dict()`
2. `core/storage.py` 的解析/迁移
3. `core/library.py` 的保存（通常自动复用）
4. 左侧列表/编辑标签需要展示时再改 `hotkey_model.py` / `main_window.py`

### 改窗口缩放

只改 `ui/widgets/frameless_resize.py`；主窗口通过 `self.resizer` 使用。

## 6. 线程模型

- 主线程：所有 QWidget 操作。
- keyboard 钩子线程：只 `signal.emit(hotkey_id)`。
- runner 线程：串行执行脚本，通过 `_Signals.finished` 回主线程。

不要在钩子/runner 线程里直接改界面，也不要在主线程里执行用户脚本。

## 7. 测试

```powershell
pytest
```

- `core` 测试不依赖 Qt。
- UI 测试用 `pytest-qt` + offscreen。
- 测试构造 `MainWindow(tmp_path)`，不会写用户目录/弹托盘；监听器进程不在单测里启动。

## 8. 代码约定

- 中文注释只解释"为什么"，不复述代码。
- 新方法尽量带类型标注和简短 docstring。
- 主窗口方法按区块放，新增功能放回对应区块，不要继续堆在文件末尾。
- 样式只写在 `theme.qss`，靠 `objectName` 选择器。
- `HotKey` 是脚本，不要新增只对"热键"有意义的字段名。
