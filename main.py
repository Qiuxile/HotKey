'''
HotKey - 热键配置与监听工具
用于创建、管理和监听全局热键，支持系统托盘运行。

功能特点：
- 导入/导出热键配置（JSON格式）
- 可视化热键配置管理
- 全局热键监听
- 系统托盘运行
- 搜索和过滤热键
- 右键菜单操作
- 代码编辑功能
'''

from hotkey.app import App


def main() -> None:
    """应用程序入口函数。"""
    app = App()
    app.run()


if __name__ == '__main__':
    main()
