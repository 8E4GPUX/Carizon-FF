"""
主窗口模块
CARIZON-模块部署工具 v2.0 — 网易云音乐风格 UI
"""
import os
import sys
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QListWidget, QAbstractItemView,
    QLineEdit, QLabel, QProgressBar, QMessageBox, QGroupBox,
    QTextEdit, QFrame, QListWidgetItem,
    QApplication, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QGraphicsDropShadowEffect, QSizePolicy,
    QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal, pyqtSlot, QObject, QThread, QMetaObject, Q_ARG
from PyQt5.QtGui import (
    QFont, QColor, QIcon, QPalette, QLinearGradient, QBrush,
    QPainter, QPixmap, QTextCursor, QTextCharFormat,
    QDragEnterEvent, QDropEvent
)

from core.deployment_engine import DeploymentEngine, DeployStatus, DeployStep
from core.package_classifier import PackageClassifier
from config.config_manager import ConfigManager, load_package_mapping, get_local_ip, resolve_target_ip
from ui.log_viewer import LogViewer
from ui.settings_dialog import SettingsDialog
from utils.logger import get_logger

logger = get_logger()


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

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
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
        self._log_viewer = None
        self._selected_files = []
        self._pkg_infos = []
        self._deploy_start_time = None
        self._deploy_timer = QTimer()
        self._deploy_timer.timeout.connect(self._update_timer)

        self._init_ui()
        self._signals = DeploySignals()
        self._connect_signals()
        self._load_recent_config()

    def _init_ui(self):
        self.setWindowTitle("CARIZON-模块部署工具 v2.0")
        self.resize(1200, 800)
        self.setMinimumSize(960, 600)

        # ====== 全局样式（网易云暗色主题） ======
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {NeteaseColors.BG_DARK}; }}
            QWidget {{ background-color: transparent; }}
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
                background-color: #0a0a14;
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
        left.setMinimumWidth(320)
        right.setMinimumWidth(400)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([480, 720])
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

        ver = QLabel("v2.0")
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
                background-color: #0a0a14;
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
        ver_label = QLabel("CARIZON  ·  v2.0")
        ver_label.setStyleSheet(
            f"font-size: 11px; color: {NeteaseColors.TEXT_MUTED}; "
            f"border: none; background: transparent;")
        layout.addWidget(ver_label)

        # 中间装饰点
        dot_mid = QLabel("·")
        dot_mid.setStyleSheet(f"color: {NeteaseColors.TEXT_MUTED}; font-size: 14px; border: none; background: transparent;")
        layout.addWidget(dot_mid)

        status_small = QLabel("就绪")
        status_small.setStyleSheet(
            f"font-size: 11px; color: {NeteaseColors.TEXT_SECONDARY}; "
            f"border: none; background: transparent;")
        layout.addWidget(status_small)

        layout.addStretch()

        # 功能按钮组
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

        self._signals.statusChanged.connect(self._on_status_changed)
        self._signals.progressUpdated.connect(self._on_progress)
        self._signals.logReceived.connect(self._on_log)

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
        self._pkg_table.setRowCount(len(self._selected_files))
        for i, (f, info) in enumerate(zip(self._selected_files, self._pkg_infos)):
            ni = QTableWidgetItem(os.path.basename(f))
            ni.setFlags(Qt.ItemIsEnabled)
            self._pkg_table.setItem(i, 0, ni)

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
        self._file_list.clear()
        self._pkg_summary.setText("")
        self._pkg_table.setRowCount(0)
        self._card_packages.set_value("0 个")
        self._update_deploy_button()

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

        if message:
            level = "ERROR" if status in (DeployStatus.FAILED, DeployStatus.ROLLING_BACK) else "INFO"
            self._append_log(level, message)

        if status in (DeployStatus.SUCCESS, DeployStatus.FAILED, DeployStatus.CANCELLED):
            self._deploy_timer.stop()
            self._deploy_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._select_btn.setEnabled(True)
            self._clear_btn.setEnabled(True)

            if status == DeployStatus.SUCCESS:
                self._flash_animation(NeteaseColors.SUCCESS)
                QMessageBox.information(self, "部署完成", "所有包部署成功！")
            elif status == DeployStatus.FAILED:
                self._flash_animation(NeteaseColors.ERROR)
                QMessageBox.critical(self, "部署失败", f"部署失败:\n{message}")

    def _flash_animation(self, color: str):
        for i in range(3):
            QTimer.singleShot(i * 300, lambda c=color: self._status_indicator.setStyleSheet(
                f"color: {c}; font-weight: bold; font-size: 15px; border: none; background: transparent;"))
            QTimer.singleShot(i * 300 + 150, lambda c=color: self._status_indicator.setStyleSheet(
                f"color: {c}; font-weight: bold; font-size: 12px; border: none; background: transparent;"))

    def _on_progress(self, percent: int, message: str):
        self._progress_bar.setValue(percent)
        self._progress_pct.setText(f"{percent}%")
        self._card_progress.set_value(f"{percent}%")

    def _on_log(self, level: str, message: str):
        self._append_log(level, message)

    # ==================== 日志 ====================

    def _append_log(self, level: str, message: str):
        ft = self._log_filter_combo.currentText()
        if ft != "全部" and level.upper() != ft:
            return
        st = self._log_search_edit.text().strip()
        if st and st.lower() not in message.lower():
            return

        cm = {"INFO": NeteaseColors.SUCCESS, "WARN": NeteaseColors.WARNING,
              "WARNING": NeteaseColors.WARNING, "ERROR": NeteaseColors.ERROR,
              "DEBUG": NeteaseColors.TEXT_MUTED}
        color = cm.get(level.upper(), NeteaseColors.TEXT_PRIMARY)
        ts = datetime.now().strftime("%H:%M:%S")
        html = f'<span style="color:{color}">[{ts}] [{level}] {message}</span><br>'
        self._log_output.insertHtml(html)
        sb = self._log_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _filter_logs(self):
        pass

    def _clear_logs(self):
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
