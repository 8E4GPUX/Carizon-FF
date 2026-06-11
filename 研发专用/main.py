"""
OTA 可视化无感部署工具 - 入口文件
"""
import sys
import os

# 确保项目根目录在 sys.path 中
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from utils.logger import LoggerManager
from ui.main_window import MainWindow


def main():
    # 高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("CARIZON-模块部署工具")
    app.setOrganizationName("CARIZON")

    # 初始化日志
    log_dir = os.path.join(project_dir, "logs")
    LoggerManager().init(log_dir)

    # 启动主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
