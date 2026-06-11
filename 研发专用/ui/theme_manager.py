"""
主题管理器 - 支持深色/浅色主题切换
"""
from PyQt5.QtCore import QObject, pyqtSignal


class ThemeManager(QObject):
    """主题管理器（单例）"""

    _instance = None
    themeChanged = pyqtSignal(str)

    LIGHT_THEME = """
        QMainWindow { background-color: #eef1f5; }
        QFrame { background-color: white; border: 1px solid #e4e4e4; border-radius: 6px; }
        QLabel { color: #333; }
        QPushButton { background-color: #ffffff; color: #333; border: 1px solid #d0d0d0; }
        QPushButton:hover { background-color: #f0f0f0; }
        QLineEdit { background-color: #fafafa; color: #333; border: 1px solid #d0d0d0; }
        QListWidget { background-color: white; color: #333; border: 1px solid #e4e4e4; }
        QTableWidget { background-color: white; color: #333; gridline-color: #f0f0f0; }
        QTextEdit { background-color: #1a1a2e; color: #e0e0e0; }
        QProgressBar { background-color: #e8e8e8; color: #444; }
        QComboBox { background-color: white; color: #333; border: 1px solid #d0d0d0; }
        QHeaderView::section { background-color: #f5f5f5; color: #555; }
    """

    DARK_THEME = """
        QMainWindow { background-color: #1a1a2e; }
        QFrame { background-color: #16213e; border: 1px solid #0f3460; border-radius: 6px; }
        QLabel { color: #e0e0e0; }
        QPushButton { background-color: #16213e; color: #e0e0e0; border: 1px solid #0f3460; }
        QPushButton:hover { background-color: #1a1a4e; }
        QLineEdit { background-color: #0f3460; color: #e0e0e0; border: 1px solid #1a1a4e; }
        QListWidget { background-color: #16213e; color: #e0e0e0; border: 1px solid #0f3460; }
        QTableWidget { background-color: #16213e; color: #e0e0e0; gridline-color: #0f3460; }
        QTextEdit { background-color: #0d1b2a; color: #e0e0e0; }
        QProgressBar { background-color: #0f3460; color: #e0e0e0; }
        QComboBox { background-color: #16213e; color: #e0e0e0; border: 1px solid #0f3460; }
        QHeaderView::section { background-color: #0f3460; color: #e0e0e0; }
    """

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._current = "light"

    @property
    def current(self) -> str:
        return self._current

    def toggle(self):
        """切换主题"""
        self._current = "dark" if self._current == "light" else "light"
        self.themeChanged.emit(self._current)

    def set_theme(self, theme: str):
        """设置主题"""
        if theme in ("light", "dark"):
            self._current = theme
            self.themeChanged.emit(self._current)

    def get_stylesheet(self) -> str:
        """获取当前主题样式表"""
        return self.DARK_THEME if self._current == "dark" else self.LIGHT_THEME
