# legacy/ —— 旧版 Tk 实现

这里保存 v2 之前的 Tkinter 实现，仅用于行为对比与回滚参考，不参与 v2 构建。

- 运行旧版：在仓库根目录执行 `python main_tk.py`
- 旧版入口：`legacy/main_tk.py`
- 旧版包：`legacy/hotkey/`

v2 功能对齐（M5）后，本目录连同根目录的 `main_tk.py` 一起删除。
`git tag v1-tk` 保存了迁移前的完整快照。

注意：`legacy/main_tk.py` 里的相对路径（如 `jsons/`）按当前工作目录解析，
请从仓库根目录启动。
