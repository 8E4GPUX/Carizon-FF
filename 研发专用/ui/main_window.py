"""
主窗口模块
CARIZON-模块部署工具 v3.0 — 网易云音乐风格 UI
"""
import os
import sys
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QListWidget, QAbstractItemView,
    QLineEdit, QLabel, QProgressBar, QMessageBox, QGroupBox,
    QTextEdit, QFrame, QListWidgetItem, QInputDialog,
    QApplication, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QGraphicsDropShadowEffect, QSizePolicy,
    QSplitter, QMenu, QDialog
)
from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal, pyqtSlot, QObject, QThread, QMetaObject, Q_ARG, QSettings
from PyQt5.QtGui import (
    QFont, QColor, QIcon, QPalette, QLinearGradient, QBrush,
    QPainter, QPixmap, QTextCursor, QTextCharFormat,
    QDragEnterEvent, QDropEvent
)

from core.deployment_engine import DeploymentEngine, DeployStatus, DeployStep
from core.package_classifier import PackageClassifier
from core.template_manager import TemplateManager, DeployTemplate
from config.config_manager import ConfigManager, load_package_mapping, get_local_ip, resolve_target_ip
from ui.log_viewer import LogViewer
from ui.settings_dialog import SettingsDialog
from ui.history_dialog import HistoryDialog
from ui.template_dialog import TemplateDialog
from utils.logger import get_logger

logger = get_logger()

# 版本号集中管理
APP_VERSION = "v3.0"


# ============================================================
# 网易云风格配色常量
# ============================================================
class NeteaseColors:
    BG_DARK = "#f5f5f5"          # 主背景 - 浅灰
    BG_CARD = "#ffffff"          # 卡片背景 - 白色
    BG_CARD_HOVER = "#f0f0f0"   # 卡片悬停
    BG_INPUT = "#fafafa"         # 输入框背景
    RED_PRIMARY = "#C20C0C"      # 网易云红 - 主色
    RED_LIGHT = "#E74C3C"        # 红色 - 亮色
    RED_DIM = "#8B0000"          # 暗红
    TEXT_PRIMARY = "#333333"     # 主文字 - 深灰
    TEXT_SECONDARY = "#666666"   # 次要文字
    TEXT_MUTED = "#999999"       # 弱化文字
    BORDER = "#e0e0e0"          # 边框 - 浅灰
    BORDER_LIGHT = "#eeeeee"    # 浅边框
    SUCCESS = "#4CAF50"          # 成功绿
    WARNING = "#FF9800"          # 警告橙
    ERROR = "#F44336"            # 错误红
    INFO = "#42A5F5"             # 信息蓝
    PROGRESS_BG = "#e8e8e8"      # 进度条背景
    SCROLLBAR = "#d0d0d0"        # 滚动条
    SCROLLBAR_HOVER = "#b0b0b0"  # 滚动条悬停


# ============================================================
# 工具函数
# ============================================================
def add_shadow(widget, blur=12, offset=2, color=QColor(0, 0, 0, 60)):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setOffset(offset, offset)
    s.setColor(color)
    widget.setGraphicsEffect(s)


def make_card_style(border_left: str = None) -> str:
    """生成网易云风格卡片样式"""
    base = f"""
        background-color: {NeteaseColors.BG_CARD};
        border: 1px solid {NeteaseColors.BORDER};
        border-radius: 8px;
    """
    if border_left:
        base += f"""
        border-left: 3px solid {border_left};
        """
    return base


def make_btn_style(bg: str, text_color: str = "#ffffff", hover: str = None) -> str:
    h = hover or bg
    return f"""
        QPushButton {{
            background-color: {bg}; color: {text_color};
            border: none; border-radius: 6px;
            font-weight: bold; font-size: 13px;
            padding: 7px 20px;
        }}
        QPushButton:hover {{
            background-color: {h};
        }}
        QPushButton:pressed {{
            background-color: {h};
            padding-top: 8px;
        }}
        QPushButton:disabled {{
            background-color: {NeteaseColors.BORDER};
            color: {NeteaseColors.TEXT_MUTED};
        }}
    """


# ============================================================
# 迷你状态标签（网易云风格）
# ============================================================
class MiniStatusCard(QFrame):
    def __init__(self, title: str, value: str, color: str = NeteaseColors.RED_PRIMARY,
                 title_size: int = 11, value_size: int = 15, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedHeight(46)
        self.setMinimumWidth(120)
        self.setStyleSheet(f"""
            MiniStatusCard {{
                {make_card_style(color)}
            }}
        """)
        add_shadow(self, blur=8, offset=1, color=QColor(0, 0, 0, 40))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 2, 12, 2)
        layout.setSpacing(8)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"font-size: {title_size}px; color: {NeteaseColors.TEXT_SECONDARY}; "
            f"font-weight: 400; border: none; background: transparent;")
        layout.addWidget(self._title_lbl)

        self._value_lbl = QLabel(value)
        self._value_lbl.setStyleSheet(
            f"font-size: {value_size}px; color: {color}; "
            f"font-weight: bold; border: none; background: transparent;")
        layout.addWidget(self._value_lbl)

        layout.addStretch()

    def set_value(self, value: str, color: str = None):
        self._value_lbl.setText(value)
        if color:
            self._color = color
            self._value_lbl.setStyleSheet(
                f"font-size: 15px; color: {color}; font-weight: bold; border: none; background: transparent;")
            self.setStyleSheet(f"MiniStatusCard {{ {make_card_style(color)} }}")

    def set_color(self, color: str):
        self._color = color
        self._value_lbl.setStyleSheet(
            f"font-size: 15px; color: {color}; font-weight: bold; border: none; background: transparent;")
        self.setStyleSheet(f"MiniStatusCard {{ {make_card_style(color)} }}")


# ============================================================
# 可拖拽文件列表
# ============================================================
class DropFileList(QListWidget):
    filesDropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self._drag_active = False
        self.setStyleSheet("""
            QListWidget { border: 2px dashed transparent; }
        """)

    def _set_drag_highlight(self, active: bool):
        """拖拽时高亮边框"""
        self._drag_active = active
        if active:
            self.setStyleSheet(
                f"QListWidget {{ border: 2px dashed {NeteaseColors.RED_PRIMARY}; "
                f"background-color: {NeteaseColors.BG_INPUT}; }}")
        else:
            self.setStyleSheet("QListWidget { border: 2px dashed transparent; }")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            self._set_drag_highlight(True)
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._set_drag_highlight(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        self._set_drag_highlight(False)
        files = []
        for url in event.mimeData().urls():
            fp = url.toLocalFile()
            if fp.lower().endswith('.zip') or os.path.isfile(fp):
                files.append(fp)
        if files:
            self.filesDropped.emit(files)
            event.acceptProposedAction()


# ============================================================
# 信号桥接
# ============================================================
class DeploySignals(QObject):
    statusChanged = pyqtSignal(object, object, str)
    progressUpdated = pyqtSignal(int, str)
    logReceived = pyqtSignal(str, str)


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):
    """CARIZON-模块部署工具 v2.0 — 网易云音乐风格"""

    STATUS_COLORS = {
        DeployStatus.IDLE: NeteaseColors.TEXT_SECONDARY,
        DeployStatus.CHECKING: NeteaseColors.INFO,
        DeployStatus.TRANSFERRING: NeteaseColors.WARNING,
        DeployStatus.BOARD_OPERATING: "#9C27B0",
        DeployStatus.WAITING_REBOOT: "#FF5722",
        DeployStatus.SUCCESS: NeteaseColors.SUCCESS,
        DeployStatus.FAILED: NeteaseColors.ERROR,
        DeployStatus.ROLLING_BACK: "#FF5722",
        DeployStatus.CANCELLED: NeteaseColors.TEXT_MUTED,
    }

    def __init__(self):
        super().__init__()
        self._config = ConfigManager()
        self._engine = DeploymentEngine()
        self._tpl_mgr = TemplateManager()
        self._log_viewer = None
        self._history_dialog = None
        self._template_dialog = None
        self._selected_files = []
        self._pkg_infos = []
        self._log_entries = []
        self._pkg_row_map = {}  # 包名 -> 表格行号
        self._deploy_start_time = None
        self._deploy_timer = QTimer()
        self._deploy_timer.timeout.connect(self._update_timer)

        self._init_ui()
        self._signals = DeploySignals()
        self._connect_signals()
        self._load_recent_config()
        self._restore_window_state()

    def _init_ui(self):
        self.setWindowTitle(f"CARIZON-模块部署工具 {APP_VERSION}")
        self.resize(1200, 800)
        self.setMinimumSize(880, 560)

        # ====== 全局样式（浅色主题） ======
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {NeteaseColors.BG_DARK}; }}
            QGroupBox {{
                font-weight: bold; font-size: 13px;
                border: 1px solid {NeteaseColors.BORDER};
                border-radius: 8px;
                margin-top: 14px; padding-top: 16px;
                background-color: {NeteaseColors.BG_CARD};
                color: {NeteaseColors.TEXT_PRIMARY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 14px;
                padding: 0 8px; color: {NeteaseColors.TEXT_SECONDARY};
            }}
            QPushButton {{
                padding: 5px 14px; border-radius: 6px;
                border: 1px solid {NeteaseColors.BORDER};
                background-color: {NeteaseColors.BG_CARD};
                color: {NeteaseColors.TEXT_PRIMARY};
                min-height: 24px; font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {NeteaseColors.BG_CARD_HOVER};
                border-color: {NeteaseColors.BORDER_LIGHT};
            }}
            QPushButton:pressed {{
                background-color: {NeteaseColors.BORDER};
            }}
            QPushButton:disabled {{
                background-color: {NeteaseColors.BG_CARD};
                color: {NeteaseColors.TEXT_MUTED};
                border-color: {NeteaseColors.BORDER};
            }}
            QLineEdit {{
                padding: 5px 10px; border: 1px solid {NeteaseColors.BORDER};
                border-radius: 6px;
                background-color: {NeteaseColors.BG_INPUT};
                color: {NeteaseColors.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {NeteaseColors.RED_PRIMARY};
                background-color: {NeteaseColors.BG_CARD};
            }}
            QLineEdit::placeholder {{
                color: {NeteaseColors.TEXT_MUTED};
            }}
            QListWidget {{
                border: 1px solid {NeteaseColors.BORDER};
                border-radius: 8px;
                background-color: {NeteaseColors.BG_CARD};
                color: {NeteaseColors.TEXT_PRIMARY};
                font-size: 13px; padding: 4px;
            }}
            QListWidget::item {{
                padding: 6px 10px; border-radius: 4px;
                margin: 1px 2px;
            }}
            QListWidget::item:selected {{
                background-color: rgba(194, 12, 12, 0.2);
                color: {NeteaseColors.RED_LIGHT};
            }}
            QListWidget::item:hover {{
                background-color: {NeteaseColors.BG_CARD_HOVER};
            }}
            QProgressBar {{
                border: none; border-radius: 4px; text-align: center;
                height: 20px;
                background-color: {NeteaseColors.PROGRESS_BG};
                font-size: 11px; font-weight: bold;
                color: {NeteaseColors.TEXT_SECONDARY};
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {NeteaseColors.RED_PRIMARY}, stop:1 {NeteaseColors.RED_LIGHT});
                border-radius: 4px;
            }}
            QTextEdit {{
                border: 1px solid {NeteaseColors.BORDER};
                border-radius: 8px;
                background-color: {NeteaseColors.BG_CARD};
                color: {NeteaseColors.TEXT_PRIMARY};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px; padding: 10px;
            }}
            QTableWidget {{
                border: 1px solid {NeteaseColors.BORDER};
                border-radius: 8px;
                background-color: {NeteaseColors.BG_CARD};
                color: {NeteaseColors.TEXT_PRIMARY};
                gridline-color: {NeteaseColors.BORDER};
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 4px 6px;
                border-bottom: 1px solid {NeteaseColors.BORDER};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(194, 12, 12, 0.15);
            }}
            QHeaderView::section {{
                background-color: {NeteaseColors.BG_INPUT};
                color: {NeteaseColors.TEXT_SECONDARY};
                border: none;
                border-bottom: 1px solid {NeteaseColors.BORDER};
                padding: 5px 8px;
                font-weight: bold; font-size: 11px;
            }}
            QScrollBar:vertical {{
                width: 4px; background: transparent;
                margin: 2px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {NeteaseColors.SCROLLBAR};
                border-radius: 2px; min-height: 25px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {NeteaseColors.SCROLLBAR_HOVER};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                height: 4px; background: transparent;
            }}
            QScrollBar::handle:horizontal {{
                background: {NeteaseColors.SCROLLBAR};
                border-radius: 2px; min-width: 25px;
            }}
            QComboBox {{
                padding: 4px 8px; border: 1px solid {NeteaseColors.BORDER};
                border-radius: 6px;
                background: {NeteaseColors.BG_CARD};
                color: {NeteaseColors.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QComboBox:hover {{
                border-color: {NeteaseColors.BORDER_LIGHT};
            }}
            QComboBox::drop-down {{
                border: none; width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {NeteaseColors.BG_CARD};
                color: {NeteaseColors.TEXT_PRIMARY};
                border: 1px solid {NeteaseColors.BORDER};
                selection-background-color: rgba(194, 12, 12, 0.2);
                selection-color: {NeteaseColors.RED_LIGHT};
            }}
            QSplitter::handle {{
                background-color: {NeteaseColors.BORDER};
                border-radius: 2px;
                margin: 8px 0;
            }}
            QSplitter::handle:hover {{
                background-color: {NeteaseColors.RED_PRIMARY};
            }}
            QSplitter::handle:pressed {{
                background-color: {NeteaseColors.RED_DIM};
            }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(16, 10, 16, 10)

        # ====== 顶部导航栏（网易云风格渐变） ======
        header = self._create_header()
        main_layout.addWidget(header)

        # ====== 核心信息栏（四张状态卡片） ======
        info_row = self._create_info_row()
        main_layout.addLayout(info_row)

        # ====== 主内容区（QSplitter 可拖拽） ======
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {NeteaseColors.BORDER};
                border-radius: 2px;
                margin: 8px 0;
            }}
            QSplitter::handle:hover {{
                background-color: {NeteaseColors.RED_PRIMARY};
            }}
        """)
        left = self._create_left_panel()
        right = self._create_right_panel()
        left.setMinimumWidth(280)
        right.setMinimumWidth(340)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([480, 720])
        self._splitter = splitter
        main_layout.addWidget(splitter, 1)

        # ====== 底部操作栏（网易云播放条风格） ======
        bottom = self._create_bottom_bar()
        main_layout.addWidget(bottom)

    # ==================== 顶部导航栏（网易云风格） ====================

    def _create_header(self):
        h = QFrame()
        h.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {NeteaseColors.BG_CARD}, stop:0.5 {NeteaseColors.BG_CARD}, stop:1 {NeteaseColors.BG_CARD});
                border: 1px solid {NeteaseColors.BORDER};
                border-radius: 10px;
            }}
        """)
        h.setFixedHeight(50)
        add_shadow(h, blur=10, offset=2, color=QColor(194, 12, 12, 30))

        layout = QHBoxLayout(h)
        layout.setContentsMargins(18, 0, 18, 0)

        # 左侧：Logo 区域（红点 + 名称）
        logo_dot = QLabel("●")
        logo_dot.setStyleSheet(
            f"color: {NeteaseColors.RED_PRIMARY}; font-size: 22px; "
            f"border: none; background: transparent; margin-right: 2px;")
        layout.addWidget(logo_dot)

        title = QLabel("CARIZON 模块部署")
        title.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {NeteaseColors.TEXT_PRIMARY}; "
            f"border: none; background: transparent; letter-spacing: 1px;")
        layout.addWidget(title)

        ver = QLabel(APP_VERSION)
        ver.setStyleSheet(
            f"font-size: 9px; color: {NeteaseColors.TEXT_MUTED}; "
            f"background: rgba(194,12,12,0.15); padding: 1px 6px; "
            f"border-radius: 4px; border: none; margin-top: 4px;")
        layout.addWidget(ver)

        layout.addSpacing(24)

        # 分隔线
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet(f"border: none; border-left: 1px solid {NeteaseColors.BORDER}; background: transparent;")
        sep1.setFixedWidth(1)
        layout.addWidget(sep1)
        layout.addSpacing(16)

        # 状态指示
        self._status_indicator = QLabel("● 就绪")
        self._status_indicator.setStyleSheet(
            f"color: {NeteaseColors.SUCCESS}; font-weight: bold; font-size: 12px; "
            f"border: none; background: transparent;")
        layout.addWidget(self._status_indicator)

        layout.addStretch()

        # 右侧：连接状态
        self._industrial_status = QLabel("● 工控机: 未连接")
        self._industrial_status.setStyleSheet(
            f"color: {NeteaseColors.TEXT_SECONDARY}; font-size: 11px; "
            f"border: none; background: transparent;")
        layout.addWidget(self._industrial_status)

        layout.addSpacing(16)

        self._board_status = QLabel("● 板端: 未连接")
        self._board_status.setStyleSheet(
            f"color: {NeteaseColors.TEXT_SECONDARY}; font-size: 11px; "
            f"border: none; background: transparent;")
        layout.addWidget(self._board_status)

        return h

    # ==================== 核心信息栏 ====================

    def _create_info_row(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)

        self._card_packages = MiniStatusCard("升级包", "0 个", NeteaseColors.RED_PRIMARY)
        row.addWidget(self._card_packages, 1)

        self._card_progress = MiniStatusCard("部署进度", "0%", NeteaseColors.WARNING)
        row.addWidget(self._card_progress, 1)

        self._card_status = MiniStatusCard("当前状态", "等待开始", "#9C27B0")
        row.addWidget(self._card_status, 1)

        self._card_time_card = MiniStatusCard("运行时间", "--:--:--", NeteaseColors.INFO)
        row.addWidget(self._card_time_card, 1)

        return row

    # ==================== 左侧面板 ====================

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # ---- 升级包选择 ----
        fg = QFrame()
        fg.setStyleSheet(f"""
            QFrame {{
                {make_card_style(NeteaseColors.RED_PRIMARY)}
            }}
        """)
        add_shadow(fg, blur=10, offset=2, color=QColor(0, 0, 0, 50))
        fl = QVBoxLayout(fg)
        fl.setSpacing(8)
        fl.setContentsMargins(14, 14, 14, 12)

        # 标题行
        title_row = QHBoxLayout()
        title1 = QLabel("升级包选择")
        title1.setStyleSheet(
            f"font-size: 15px; color: {NeteaseColors.TEXT_PRIMARY}; "
            f"font-weight: bold; border: none; background: transparent; "
            f"padding-bottom: 2px;")
        title_row.addWidget(title1)

        # 小红点装饰
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {NeteaseColors.RED_PRIMARY}; font-size: 8px; border: none; background: transparent; margin-bottom: 4px;")
        title_row.addWidget(dot)
        title_row.addStretch()
        fl.addLayout(title_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._select_btn = QPushButton("选择文件")
        self._select_btn.setStyleSheet(make_btn_style(NeteaseColors.RED_PRIMARY, "#ffffff", NeteaseColors.RED_LIGHT))
        self._select_btn.clicked.connect(self._select_files)
        btn_row.addWidget(self._select_btn)

        self._clear_btn = QPushButton("清空")
        self._clear_btn.setStyleSheet(make_btn_style(NeteaseColors.BG_INPUT, NeteaseColors.TEXT_SECONDARY, NeteaseColors.BG_CARD_HOVER))
        self._clear_btn.clicked.connect(self._clear_files)
        btn_row.addWidget(self._clear_btn)

        # 模板功能合并为下拉菜单
        self._tpl_btn = QPushButton("模板 ▾")
        self._tpl_btn.setStyleSheet(make_btn_style(NeteaseColors.BG_INPUT, NeteaseColors.TEXT_SECONDARY, NeteaseColors.BG_CARD_HOVER))
        self._tpl_menu = QMenu(self)
        self._tpl_menu.addAction("保存当前为模板", self._save_template)
        self._tpl_menu.addAction("加载模板", self._load_template)
        self._tpl_menu.addAction("管理模板", self._open_template_dialog)
        self._tpl_btn.setMenu(self._tpl_menu)
        btn_row.addWidget(self._tpl_btn)

        btn_row.addStretch()
        fl.addLayout(btn_row)

        self._file_list = DropFileList()
        self._file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._file_list.setMinimumHeight(100)
        self._file_list.setAlternatingRowColors(True)
        self._file_list.setStyleSheet(f"""
            QListWidget {{
                alternate-background-color: {NeteaseColors.BG_INPUT};
                font-size: 14px; padding: 4px;
            }}
            QListWidget::item {{ padding: 6px 10px; border-radius: 4px; }}
        """)
        self._file_list.filesDropped.connect(self._on_files_dropped)
        fl.addWidget(self._file_list, 1)

        self._pkg_summary = QLabel("")
        self._pkg_summary.setStyleSheet(
            f"color: {NeteaseColors.TEXT_SECONDARY}; font-size: 12px; "
            f"padding: 2px 4px; border: none; background: transparent;")
        self._pkg_summary.setWordWrap(True)
        fl.addWidget(self._pkg_summary)

        layout.addWidget(fg, 2)

        # ---- 部署进度 ----
        pg = QFrame()
        pg.setStyleSheet(f"""
            QFrame {{
                {make_card_style(NeteaseColors.WARNING)}
            }}
        """)
        add_shadow(pg, blur=10, offset=2, color=QColor(0, 0, 0, 50))
        pl = QVBoxLayout(pg)
        pl.setSpacing(8)
        pl.setContentsMargins(14, 14, 14, 12)

        title_row2 = QHBoxLayout()
        title2 = QLabel("部署进度")
        title2.setStyleSheet(
            f"font-size: 15px; color: {NeteaseColors.TEXT_PRIMARY}; "
            f"font-weight: bold; border: none; background: transparent;")
        title_row2.addWidget(title2)
        dot2 = QLabel("●")
        dot2.setStyleSheet(f"color: {NeteaseColors.WARNING}; font-size: 8px; border: none; background: transparent; margin-bottom: 4px;")
        title_row2.addWidget(dot2)
        title_row2.addStretch()
        pl.addLayout(title_row2)

        # 当前步骤提示（部署中醒目显示）
        self._current_step_label = QLabel("等待部署")
        self._current_step_label.setStyleSheet(
            f"font-size: 13px; color: {NeteaseColors.TEXT_SECONDARY}; "
            f"border: none; background: transparent; padding-bottom: 2px;")
        self._current_step_label.setWordWrap(True)
        pl.addWidget(self._current_step_label)

        pbar = QHBoxLayout()
        self._progress_bar = QProgressBar()
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("  %p%  -  当前包: %v/%m ")
        self._progress_bar.setFixedHeight(24)
        pbar.addWidget(self._progress_bar, 1)

        self._progress_pct = QLabel("0%")
        self._progress_pct.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {NeteaseColors.WARNING}; "
            f"border: none; background: transparent;")
        self._progress_pct.setFixedWidth(50)
        self._progress_pct.setAlignment(Qt.AlignCenter)
        pbar.addWidget(self._progress_pct)

        pl.addLayout(pbar)

        self._pkg_table = QTableWidget(0, 4)
        self._pkg_table.setHorizontalHeaderLabels(["包名", "类型", "状态", "耗时"])
        self._pkg_table.horizontalHeader().setStretchLastSection(True)
        self._pkg_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._pkg_table.setColumnWidth(1, 130)
        self._pkg_table.setColumnWidth(2, 80)
        self._pkg_table.setColumnWidth(3, 80)
        self._pkg_table.verticalHeader().setVisible(False)
        self._pkg_table.setSelectionMode(QAbstractItemView.NoSelection)
        self._pkg_table.setStyleSheet(f"""
            QTableWidget {{ font-size: 13px; border-radius: 8px; }}
            QTableWidget::item {{ padding: 4px 8px; }}
        """)
        pl.addWidget(self._pkg_table)

        layout.addWidget(pg, 3)
        return panel

    # ==================== 右侧面板 ====================

    def _create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        lg = QFrame()
        lg.setStyleSheet(f"""
            QFrame {{
                {make_card_style(NeteaseColors.INFO)}
            }}
        """)
        add_shadow(lg, blur=10, offset=2, color=QColor(0, 0, 0, 50))
        ll = QVBoxLayout(lg)
        ll.setSpacing(8)
        ll.setContentsMargins(14, 14, 14, 12)

        # 标题行
        title_row3 = QHBoxLayout()
        title3 = QLabel("实时日志")
        title3.setStyleSheet(
            f"font-size: 15px; color: {NeteaseColors.TEXT_PRIMARY}; "
            f"font-weight: bold; border: none; background: transparent;")
        title_row3.addWidget(title3)
        dot3 = QLabel("●")
        dot3.setStyleSheet(f"color: {NeteaseColors.INFO}; font-size: 8px; border: none; background: transparent; margin-bottom: 4px;")
        title_row3.addWidget(dot3)
        title_row3.addStretch()
        ll.addLayout(title_row3)

        # 工具栏
        tb = QHBoxLayout()
        tb.setSpacing(8)

        fl = QLabel("过滤:")
        fl.setStyleSheet(f"font-size: 12px; color: {NeteaseColors.TEXT_SECONDARY}; border: none; background: transparent;")
        tb.addWidget(fl)

        self._log_filter_combo = QComboBox()
        self._log_filter_combo.addItems(["全部", "INFO", "WARN", "ERROR"])
        self._log_filter_combo.setFixedWidth(80)
        self._log_filter_combo.currentIndexChanged.connect(self._filter_logs)
        tb.addWidget(self._log_filter_combo)

        self._log_search_edit = QLineEdit()
        self._log_search_edit.setPlaceholderText("搜索日志...")
        self._log_search_edit.setStyleSheet(
            f"font-size: 12px; padding: 5px 10px; "
            f"background-color: {NeteaseColors.BG_INPUT};")
        self._log_search_edit.returnPressed.connect(self._filter_logs)
        tb.addWidget(self._log_search_edit, 1)

        self._log_clear_btn = QPushButton("清空")
        self._log_clear_btn.setFixedWidth(55)
        self._log_clear_btn.setStyleSheet(make_btn_style(NeteaseColors.BG_INPUT, NeteaseColors.TEXT_SECONDARY, NeteaseColors.BG_CARD_HOVER))
        self._log_clear_btn.clicked.connect(self._clear_logs)
        tb.addWidget(self._log_clear_btn)

        ll.addLayout(tb)

        self._log_output = QTextEdit()
        self._log_output.setReadOnly(True)
        self._log_output.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {NeteaseColors.BORDER};
                border-radius: 8px;
                background-color: {NeteaseColors.BG_CARD};
                color: {NeteaseColors.TEXT_PRIMARY};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px; padding: 12px;
            }}
        """)
        ll.addWidget(self._log_output, 1)

        layout.addWidget(lg, 1)
        return panel

    # ==================== 底部操作栏（网易云播放条风格） ====================

    def _create_bottom_bar(self):
        bar = QFrame()
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {NeteaseColors.BG_CARD};
                border: 1px solid {NeteaseColors.BORDER};
                border-radius: 10px;
                border-top: 2px solid {NeteaseColors.RED_PRIMARY};
            }}
        """)
        bar.setFixedHeight(54)
        add_shadow(bar, blur=12, offset=2, color=QColor(194, 12, 12, 25))

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(10)

        # 左侧：版本信息
        ver_label = QLabel(f"CARIZON  ·  {APP_VERSION}")
        ver_label.setStyleSheet(
            f"font-size: 11px; color: {NeteaseColors.TEXT_MUTED}; "
            f"border: none; background: transparent;")
        layout.addWidget(ver_label)

        # 中间装饰点
        dot_mid = QLabel("·")
        dot_mid.setStyleSheet(f"color: {NeteaseColors.TEXT_MUTED}; font-size: 14px; border: none; background: transparent;")
        layout.addWidget(dot_mid)

        # 底部状态：显示当前步骤（与顶部/卡片联动）
        self._step_small = QLabel("就绪")
        self._step_small.setStyleSheet(
            f"font-size: 11px; color: {NeteaseColors.TEXT_SECONDARY}; "
            f"border: none; background: transparent;")
        layout.addWidget(self._step_small)

        layout.addStretch()

        # 功能按钮组
        self._self_check_btn = QPushButton("环境自检")
        self._self_check_btn.setStyleSheet(make_btn_style(NeteaseColors.BG_INPUT, NeteaseColors.TEXT_SECONDARY, NeteaseColors.BG_CARD_HOVER))
        self._self_check_btn.clicked.connect(self._run_self_check)
        layout.addWidget(self._self_check_btn)

        self._history_btn = QPushButton("历史")
        self._history_btn.setStyleSheet(make_btn_style(NeteaseColors.BG_INPUT, NeteaseColors.TEXT_SECONDARY, NeteaseColors.BG_CARD_HOVER))
        self._history_btn.clicked.connect(self._open_history_dialog)
        layout.addWidget(self._history_btn)

        self._settings_btn = QPushButton("设置")
        self._settings_btn.setStyleSheet(make_btn_style(NeteaseColors.BG_INPUT, NeteaseColors.TEXT_SECONDARY, NeteaseColors.BG_CARD_HOVER))
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)

        self._log_btn = QPushButton("日志")
        self._log_btn.setStyleSheet(make_btn_style(NeteaseColors.BG_INPUT, NeteaseColors.TEXT_SECONDARY, NeteaseColors.BG_CARD_HOVER))
        self._log_btn.clicked.connect(self._open_log_viewer)
        layout.addWidget(self._log_btn)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"border: none; border-left: 1px solid {NeteaseColors.BORDER}; background: transparent;")
        sep.setFixedWidth(1)
        layout.addWidget(sep)

        # 操作按钮组（网易云播放按钮风格）
        self._deploy_btn = QPushButton("▶  部署")
        self._deploy_btn.setStyleSheet(make_btn_style(NeteaseColors.RED_PRIMARY, "#ffffff", NeteaseColors.RED_LIGHT))
        self._deploy_btn.clicked.connect(self._start_deploy)
        layout.addWidget(self._deploy_btn)

        self._stop_btn = QPushButton("■  停止")
        self._stop_btn.setStyleSheet(make_btn_style("#555", NeteaseColors.TEXT_SECONDARY, "#666"))
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_deploy)
        layout.addWidget(self._stop_btn)

        return bar

    # ==================== 信号连接 ====================

    def _connect_signals(self):
        self._engine.set_status_callback(
            lambda s, st, m: self._signals.statusChanged.emit(s, st, m))
        self._engine.set_progress_callback(
            lambda p, m: self._signals.progressUpdated.emit(p, m))
        self._engine.set_log_callback(
            lambda l, m: self._signals.logReceived.emit(l, m))
        self._engine.set_confirm_callback(self._threadsafe_confirm)
        self._engine.set_conn_status_callback(self._on_conn_status)
        self._engine.set_package_callback(self._on_pkg_status)

        self._signals.statusChanged.connect(self._on_status_changed)
        self._signals.progressUpdated.connect(self._on_progress)
        self._signals.logReceived.connect(self._on_log)

        # 日志搜索实时过滤
        self._log_search_edit.textChanged.connect(self._filter_logs)

    def _threadsafe_confirm(self, title: str, message: str) -> bool:
        self._confirm_result = False
        QMetaObject.invokeMethod(self, "_do_confirm", Qt.BlockingQueuedConnection,
                                 Q_ARG(str, title), Q_ARG(str, message))
        return self._confirm_result

    @pyqtSlot(str, str)
    def _do_confirm(self, title: str, message: str):
        r = QMessageBox.question(self, title, message, QMessageBox.Yes | QMessageBox.No)
        self._confirm_result = (r == QMessageBox.Yes)

    # ==================== 文件选择 ====================

    def _add_files(self, files: list):
        if not files:
            return
        existing = set(self._selected_files)
        new_files = [f for f in files if f not in existing]
        if not new_files:
            return

        classifier = PackageClassifier(load_package_mapping())
        for f in new_files:
            self._selected_files.append(f)
            fn = os.path.basename(f)
            pi = classifier.classify(fn)
            self._pkg_infos.append(pi)
            item = QListWidgetItem()
            if pi.is_known:
                item.setText(f"  {fn}")
                item.setForeground(QColor(NeteaseColors.TEXT_PRIMARY))
                item.setData(Qt.UserRole, pi.pkg_type)
            else:
                item.setText(f"  {fn}  [⚠]")
                item.setForeground(QColor(NeteaseColors.WARNING))
                item.setData(Qt.UserRole, "unknown")
            self._file_list.addItem(item)

        self._update_pkg_summary()
        self._card_packages.set_value(f"{len(self._selected_files)} 个")
        self._update_deploy_button()
        self._populate_pkg_table()

    def _select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择升级包", "", "压缩包 (*.zip);;所有文件 (*)")
        self._add_files(files)

    def _on_files_dropped(self, files: list):
        self._add_files(files)

    def _update_pkg_summary(self):
        if not self._pkg_infos:
            self._pkg_summary.setText("")
            return
        known = [p for p in self._pkg_infos if p.is_known]
        unknown = [p for p in self._pkg_infos if not p.is_known]
        parts = []
        if known:
            parts.append(f"✅ {len(known)} 个可识别")
        if unknown:
            parts.append(f"❌ {len(unknown)} 个未识别")
        parts.append(f"共 {len(self._pkg_infos)} 个文件")
        self._pkg_summary.setText("  |  ".join(parts))

    def _populate_pkg_table(self):
        self._pkg_row_map.clear()
        self._pkg_table.setRowCount(len(self._selected_files))
        for i, (f, info) in enumerate(zip(self._selected_files, self._pkg_infos)):
            ni = QTableWidgetItem(os.path.basename(f))
            ni.setFlags(Qt.ItemIsEnabled)
            self._pkg_table.setItem(i, 0, ni)
            self._pkg_row_map[info.filename] = i

            ti = QTableWidgetItem(info.target_dir if info.target_dir and info.target_dir != "unknown" else info.pkg_type.upper())
            ti.setFlags(Qt.ItemIsEnabled)
            ti.setTextAlignment(Qt.AlignCenter)
            self._pkg_table.setItem(i, 1, ti)

            si = QTableWidgetItem("等待中")
            si.setFlags(Qt.ItemIsEnabled)
            si.setTextAlignment(Qt.AlignCenter)
            si.setForeground(QColor(NeteaseColors.TEXT_MUTED))
            self._pkg_table.setItem(i, 2, si)

            tmi = QTableWidgetItem("--:--")
            tmi.setFlags(Qt.ItemIsEnabled)
            tmi.setTextAlignment(Qt.AlignCenter)
            self._pkg_table.setItem(i, 3, tmi)

    def _clear_files(self):
        """清空文件列表（带确认）"""
        if not self._selected_files:
            return

        reply = QMessageBox.question(
            self, "确认清空",
            f"确定要清空 {len(self._selected_files)} 个已选文件吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self._selected_files = []
        self._pkg_infos = []
        self._pkg_row_map.clear()
        self._file_list.clear()
        self._pkg_summary.setText("")
        self._pkg_table.setRowCount(0)
        self._card_packages.set_value("0 个")
        self._update_deploy_button()

    # ==================== 部署模板 ====================

    def _save_template(self):
        """保存当前文件列表 + 配置为模板"""
        if not self._selected_files:
            QMessageBox.warning(self, "提示", "请先选择升级包文件再保存模板")
            return

        name, ok = QInputDialog.getText(
            self, "保存模板", "请输入模板名称：")
        if not ok or not name.strip():
            return
        name = name.strip()

        # 与已有模板重名时覆盖
        if self._tpl_mgr.load(name) is not None:
            ret = QMessageBox.question(
                self, "模板已存在", f"模板 [{name}] 已存在，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ret != QMessageBox.Yes:
                return

        # 记录包名（不含路径）
        packages = [os.path.basename(p) for p in self._selected_files]
        config_snapshot = self._config.get_all()
        template = DeployTemplate(name, config_snapshot, packages)
        if self._tpl_mgr.save(template):
            QMessageBox.information(self, "成功", f"模板 [{name}] 已保存")
        else:
            QMessageBox.critical(self, "失败", "模板保存失败")

    def _load_template(self):
        """载入模板：填充文件列表与配置"""
        templates = self._tpl_mgr.list_templates()
        if not templates:
            QMessageBox.information(self, "提示", "暂无可用模板，请先保存模板")
            return

        items = [f"{t.name}  ({len(t.packages)} 个包)" for t in templates]
        choice, ok = QInputDialog.getItem(
            self, "加载模板", "选择模板：", items, 0, False)
        if not ok:
            return
        name = items[choice].split("  (")[0]
        template = self._tpl_mgr.load(name)
        if template is None:
            QMessageBox.critical(self, "失败", f"模板 [{name}] 加载失败")
            return

        # 应用模板中的配置
        if template.config:
            self._config.update(template.config)

        # 填充文件列表（模板中记录的是包名，需弹窗让用户选择实际文件路径）
        if template.packages:
            files, _ = QFileDialog.getOpenFileNames(
                self, f"选择模板 [{name}] 对应的升级包（{len(template.packages)} 个）",
                "", "压缩包 (*.zip);;所有文件 (*)")
            self._add_files(files)
            if len(files) != len(template.packages):
                QMessageBox.warning(
                    self, "提示",
                    f"模板 [{name}] 包含 {len(template.packages)} 个包，"
                    f"本次选择了 {len(files)} 个，请核对！")
        else:
            self._add_files([])

        self._load_recent_config()
        QMessageBox.information(self, "成功", f"已加载模板 [{name}]")

    # ==================== 部署控制 ====================

    def _start_deploy(self):
        if not self._selected_files:
            QMessageBox.warning(self, "提示", "请先选择升级包文件")
            return
        config = self._config
        if not config.get("工控机_IP") or not config.get("板端_IP"):
            ret = QMessageBox.warning(self, "配置未完成",
                "工控机或板端 IP 未配置，是否前往设置？",
                QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.Yes:
                self._open_settings()
            return

        # 部署前清单确认
        if not self._confirm_deploy_plan():
            return

        self._deploy_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._select_btn.setEnabled(False)
        self._clear_btn.setEnabled(False)

        self._log_output.clear()
        self._progress_bar.setValue(0)
        self._progress_pct.setText("0%")
        self._card_progress.set_value("0%")

        for i in range(self._pkg_table.rowCount()):
            self._pkg_table.item(i, 2).setText("等待中")
            self._pkg_table.item(i, 2).setForeground(QColor(NeteaseColors.TEXT_MUTED))

        self._deploy_start_time = datetime.now()
        self._deploy_timer.start(1000)
        self._engine.start_deploy(self._selected_files, [], False)

    def _confirm_deploy_plan(self) -> bool:
        """部署前展示清单并确认

        Returns:
            用户确认返回 True
        """
        industrial_ip = self._config.get("工控机_IP", "")
        board_ip = self._config.get("板端_IP", "")

        lines = [
            f"🖥  工控机: {industrial_ip}",
            f"📱  板端: {board_ip}",
            f"📦  升级包 ({len(self._pkg_infos)} 个):",
        ]
        for info in self._pkg_infos:
            target = info.target_dir if info.target_dir and info.target_dir != "unknown" else info.pkg_type.upper()
            mark = "✅" if info.is_known else "❌"
            lines.append(f"  {mark} {info.filename}  →  {target}")
        unknown = [p for p in self._pkg_infos if not p.is_known]
        if unknown:
            lines.append("\n⚠️ 存在未识别类型的包，请确认包文件正确！")

        reply = QMessageBox.question(
            self, "确认部署",
            "\n".join(lines) + "\n\n确定开始部署吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes

    def _stop_deploy(self):
        self._engine.cancel()
        self._append_log("WARN", "⛔ 用户请求停止部署...")

    def _update_timer(self):
        if self._deploy_start_time:
            e = datetime.now() - self._deploy_start_time
            s = int(e.total_seconds())
            h, m, s = s // 3600, (s % 3600) // 60, s % 60
            self._card_time_card.set_value(f"{h:02d}:{m:02d}:{s:02d}")

    # ==================== 回调 ====================

    def _on_status_changed(self, status: DeployStatus, step: DeployStep, message: str):
        color = self.STATUS_COLORS.get(status, NeteaseColors.TEXT_SECONDARY)
        names = {
            DeployStatus.IDLE: "就绪", DeployStatus.CHECKING: "检查中",
            DeployStatus.TRANSFERRING: "传输中", DeployStatus.BOARD_OPERATING: "板端操作中",
            DeployStatus.WAITING_REBOOT: "等待重启", DeployStatus.SUCCESS: "部署成功",
            DeployStatus.FAILED: "部署失败", DeployStatus.ROLLING_BACK: "回滚中",
            DeployStatus.CANCELLED: "已取消",
        }
        name = names.get(status, status.value)

        # 顶部状态
        self._status_indicator.setText(f"● {name}")
        self._status_indicator.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 12px; border: none; background: transparent;")

        # 卡片状态
        sc = {
            DeployStatus.SUCCESS: NeteaseColors.SUCCESS, DeployStatus.FAILED: NeteaseColors.ERROR,
            DeployStatus.CHECKING: NeteaseColors.INFO, DeployStatus.TRANSFERRING: NeteaseColors.WARNING,
            DeployStatus.BOARD_OPERATING: "#9C27B0", DeployStatus.WAITING_REBOOT: "#FF5722",
            DeployStatus.ROLLING_BACK: "#FF5722", DeployStatus.CANCELLED: NeteaseColors.TEXT_MUTED,
        }
        self._card_status.set_value(name)
        self._card_status.set_color(sc.get(status, NeteaseColors.TEXT_SECONDARY))

        # 当前步骤提示（部署进度卡片 + 底部栏联动）
        step_name = step.value if step else ""
        if status == DeployStatus.IDLE:
            self._current_step_label.setText("等待部署")
            self._current_step_label.setStyleSheet(
                f"font-size: 13px; color: {NeteaseColors.TEXT_SECONDARY}; "
                f"border: none; background: transparent; padding-bottom: 2px;")
            self._step_small.setText("就绪")
        elif status in (DeployStatus.SUCCESS, DeployStatus.FAILED, DeployStatus.CANCELLED):
            self._current_step_label.setText("—")
            self._current_step_label.setStyleSheet(
                f"font-size: 13px; color: {NeteaseColors.TEXT_SECONDARY}; "
                f"border: none; background: transparent; padding-bottom: 2px;")
            self._step_small.setText(name)
        else:
            self._current_step_label.setText(f"▸ {step_name}")
            self._current_step_label.setStyleSheet(
                f"font-size: 13px; color: {NeteaseColors.RED_PRIMARY}; font-weight: bold; "
                f"border: none; background: transparent; padding-bottom: 2px;")
            self._step_small.setText(step_name)

        if message:
            level = "ERROR" if status in (DeployStatus.FAILED, DeployStatus.ROLLING_BACK) else "INFO"
            self._append_log(level, message)

        if status in (DeployStatus.SUCCESS, DeployStatus.FAILED, DeployStatus.CANCELLED):
            self._deploy_timer.stop()
            self._deploy_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._select_btn.setEnabled(True)
            self._clear_btn.setEnabled(True)

            # 显示本次部署总耗时
            if self._deploy_start_time:
                dur = int((datetime.now() - self._deploy_start_time).total_seconds())
                h, m, s = dur // 3600, (dur % 3600) // 60, dur % 60
                self._card_time_card.set_value(f"{h:02d}:{m:02d}:{s:02d}")
                self._step_small.setText(f"{name} · 总耗时 {h:02d}:{m:02d}:{s:02d}")

            if status == DeployStatus.SUCCESS:
                self._flash_animation(NeteaseColors.SUCCESS)
                ret = QMessageBox.question(
                    self, "部署完成", "所有包部署成功！\n\n是否清空文件列表？",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if ret == QMessageBox.Yes:
                    self._clear_files()
            elif status == DeployStatus.FAILED:
                self._flash_animation(NeteaseColors.ERROR)
                self._show_failure_advice(message)

    def _flash_animation(self, color: str):
        for i in range(3):
            QTimer.singleShot(i * 300, lambda c=color: self._status_indicator.setStyleSheet(
                f"color: {c}; font-weight: bold; font-size: 15px; border: none; background: transparent;"))
            QTimer.singleShot(i * 300 + 150, lambda c=color: self._status_indicator.setStyleSheet(
                f"color: {c}; font-weight: bold; font-size: 12px; border: none; background: transparent;"))

    def _show_failure_advice(self, message: str):
        """部署失败时按错误类型给出可操作建议"""
        msg = message or "未知错误"
        advice = ""

        if "认证失败" in msg or "Authentication" in msg:
            advice = ("认证失败：请检查设置中的用户名/密码/密钥文件是否正确，"
                      "以及工控机→板端是否已配置免密登录。")
        elif "不可达" in msg or "unreachable" in msg.lower():
            advice = "主机不可达：请检查 IP 地址、网络连通性和网线/交换机状态。"
        elif "超时" in msg or "timeout" in msg.lower():
            advice = "连接超时：请确认目标设备在线，可尝试增大 SSH 超时时间。"
        elif "空间不足" in msg or "No space" in msg:
            advice = "空间不足：工具已尝试自动清理 /ota 目录，仍不足时请人工清理板端空间。"
        elif "免密" in msg:
            advice = "请在工控机上执行 ssh-copy-id 配置到板端 root 的免密登录后重试。"
        elif "未识别" in msg or "无法识别" in msg:
            advice = "存在未识别的包类型：请在 package_mapping.json 中补充关键字映射。"
        elif "回滚" in msg:
            advice = "部署已失败并尝试回滚，若回滚未完全成功请人工检查板端状态。"
        else:
            advice = "请查看日志面板定位具体失败环节，必要时检查板端 /ota 目录和系统日志。"

        QMessageBox.critical(self, "部署失败", f"部署失败:\n{msg}\n\n💡 建议：{advice}")

    def _on_progress(self, percent: int, message: str):
        self._progress_bar.setValue(percent)
        self._progress_pct.setText(f"{percent}%")
        self._card_progress.set_value(f"{percent}%")

    def _on_log(self, level: str, message: str):
        self._append_log(level, message)

    # ==================== 连接状态 / 包状态 ====================

    def _on_conn_status(self, role: str, connected: bool):
        """连接状态实时更新（顶部导航栏）"""
        label = self._industrial_status if role == "工控机" else self._board_status
        ip = self._config.get("工控机_IP", "") if role == "工控机" else self._config.get("板端_IP", "")
        if connected:
            label.setText(f"● {role}: {ip} 已连接")
            label.setStyleSheet(
                f"color: {NeteaseColors.SUCCESS}; font-size: 11px; "
                f"border: none; background: transparent;")
        else:
            label.setText(f"● {role}: 连接失败")
            label.setStyleSheet(
                f"color: {NeteaseColors.ERROR}; font-size: 11px; "
                f"border: none; background: transparent;")

    def _on_pkg_status(self, filename: str, status: str, message: str):
        """包表格状态列实时更新"""
        row = self._pkg_row_map.get(filename)
        if row is None:
            return
        item = self._pkg_table.item(row, 2)
        if item is None:
            return

        status_map = {
            "transferring": ("传输中", NeteaseColors.WARNING),
            "operating": ("板端操作中", "#9C27B0"),
            "waiting_reboot": ("等待重启", "#FF5722"),
            "success": ("成功", NeteaseColors.SUCCESS),
            "failed": ("失败", NeteaseColors.ERROR),
        }
        text, color = status_map.get(status, (message or status, NeteaseColors.TEXT_MUTED))
        item.setText(text)
        item.setForeground(QColor(color))

    # ==================== 环境自检 ====================

    def _run_self_check(self):
        """一键环境自检"""
        if self._engine.is_running:
            QMessageBox.warning(self, "提示", "部署正在进行中，无法自检")
            return

        self._append_log("INFO", "🔍 开始环境自检...")
        self._self_check_btn.setEnabled(False)

        def on_result(items):
            lines = ["环境自检结果：", ""]
            all_ok = True
            for it in items:
                mark = "✅" if it["ok"] else "❌"
                if not it["ok"]:
                    all_ok = False
                lines.append(f"{mark} {it['name']}: {it['detail']}")
            lines.append("")
            lines.append("✅ 全部通过，可以部署！" if all_ok else "⚠️ 存在问题，请按提示处理后重试")

            self._append_log("INFO" if all_ok else "ERROR",
                             "环境自检: " + ("全部通过" if all_ok else "存在异常"))
            self._self_check_btn.setEnabled(True)
            QMessageBox.information(self, "环境自检",
                                    "\n".join(lines))

        if not self._engine.run_self_check(on_result):
            self._self_check_btn.setEnabled(True)
            QMessageBox.warning(self, "提示", "自检无法启动，请检查是否正在部署")

    # ==================== 历史 / 模板对话框 ====================

    def _open_history_dialog(self):
        if self._history_dialog is None:
            self._history_dialog = HistoryDialog(self)
        self._history_dialog.refresh()
        self._history_dialog.show()
        self._history_dialog.raise_()
        self._history_dialog.activateWindow()

    def _open_template_dialog(self):
        if self._template_dialog is None:
            self._template_dialog = TemplateDialog(self)
        self._template_dialog.refresh()
        self._template_dialog.show()
        self._template_dialog.raise_()
        self._template_dialog.activateWindow()

    # ==================== 窗口状态记忆 ====================

    def _restore_window_state(self):
        """恢复上次的窗口大小与分栏比例"""
        settings = QSettings("CARIZON", "ota_deploy_tool")
        geom = settings.value("geometry")
        if geom is not None:
            self.restoreGeometry(geom)
        sizes = settings.value("splitter_sizes")
        if sizes and hasattr(self, "_splitter"):
            try:
                self._splitter.setSizes([int(x) for x in sizes])
            except Exception:
                pass

    def closeEvent(self, event):
        """保存窗口状态"""
        settings = QSettings("CARIZON", "ota_deploy_tool")
        settings.setValue("geometry", self.saveGeometry())
        if hasattr(self, "_splitter"):
            settings.setValue("splitter_sizes", self._splitter.sizes())
        super().closeEvent(event)

    # ==================== 日志 ====================

    def _append_log(self, level: str, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_entries.append((level, message, ts))

        # 实时显示时套用当前过滤条件
        if not self._log_entry_matches(level, message):
            return

        self._insert_log_html(level, message, ts)

    def _log_entry_matches(self, level: str, message: str) -> bool:
        """判断日志条目是否符合当前过滤/搜索条件"""
        ft = self._log_filter_combo.currentText()
        if ft != "全部" and level.upper() != ft:
            return False
        st = self._log_search_edit.text().strip()
        if st and st.lower() not in message.lower():
            return False
        return True

    def _insert_log_html(self, level: str, message: str, ts: str = None):
        cm = {"INFO": NeteaseColors.SUCCESS, "WARN": NeteaseColors.WARNING,
              "WARNING": NeteaseColors.WARNING, "ERROR": NeteaseColors.ERROR,
              "DEBUG": NeteaseColors.TEXT_MUTED}
        color = cm.get(level.upper(), NeteaseColors.TEXT_PRIMARY)
        if ts is None:
            ts = datetime.now().strftime("%H:%M:%S")
        html = f'<span style="color:{color}">[{ts}] [{level}] {message}</span><br>'
        self._log_output.insertHtml(html)
        sb = self._log_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _filter_logs(self):
        """按当前过滤条件重绘日志"""
        self._log_output.clear()
        for level, message, ts in self._log_entries:
            if self._log_entry_matches(level, message):
                self._insert_log_html(level, message, ts)

    def _clear_logs(self):
        self._log_entries.clear()
        self._log_output.clear()

    # ==================== 辅助 ====================

    def _update_deploy_button(self):
        self._deploy_btn.setEnabled(len(self._selected_files) > 0)

    def _load_recent_config(self):
        config = self._config
        local_ip = get_local_ip()
        if local_ip:
            if not config.get("工控机_IP"):
                config.set("工控机_IP", local_ip)
                logger.info(f"自动检测工控机 IP: {local_ip}")
            target_ip = resolve_target_ip(local_ip)
            if target_ip:
                old = config.get("板端_IP", "")
                if not old or old != target_ip:
                    config.set("板端_IP", target_ip)
                    logger.info(f"自动匹配板端 IP: {local_ip} -> {target_ip}")

        if config.get("板端_IP"):
            self._board_status.setText(f"● 板端: {config.get('板端_IP')}")
            self._board_status.setStyleSheet(
                f"color: {NeteaseColors.SUCCESS}; font-size: 11px; border: none; background: transparent;")
        if config.get("工控机_IP"):
            self._industrial_status.setText(f"● 工控机: {config.get('工控机_IP')}")
            self._industrial_status.setStyleSheet(
                f"color: {NeteaseColors.SUCCESS}; font-size: 11px; border: none; background: transparent;")

    # ==================== 菜单 ====================

    def _open_settings(self):
        d = SettingsDialog(self)
        d.exec_()
        if d.is_modified:
            self._load_recent_config()

    def _open_log_viewer(self):
        if self._log_viewer is None:
            self._log_viewer = LogViewer(self)
        self._log_viewer.show()
        self._log_viewer.raise_()
        self._log_viewer.activateWindow()
