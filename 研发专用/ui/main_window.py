"""
主窗口模块
CARIZON-模块部署工具 v2.0 — 工业级 UI 优化版
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
# 工具函数
# ============================================================
def add_shadow(widget, blur=10, offset=1, color=QColor(0, 0, 0, 25)):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setOffset(offset, offset)
    s.setColor(color)
    widget.setGraphicsEffect(s)


# ============================================================
# 迷你状态标签
# ============================================================
class MiniStatusCard(QFrame):
    def __init__(self, title: str, value: str, color: str = "#2196F3",
                 title_size: int = 12, value_size: int = 14, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedHeight(40)
        self.setMinimumWidth(140)
        self.setStyleSheet(f"""
            MiniStatusCard {{
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                border-left: 3px solid {color};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(6)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(f"font-size: {title_size}px; color: #888; font-weight: 500; border: none;")
        layout.addWidget(self._title_lbl)

        self._value_lbl = QLabel(value)
        self._value_lbl.setStyleSheet(f"font-size: {value_size}px; color: {color}; font-weight: bold; border: none;")
        layout.addWidget(self._value_lbl)

        layout.addStretch()

    def set_value(self, value: str, color: str = None):
        self._value_lbl.setText(value)
        if color:
            self._color = color
            self._value_lbl.setStyleSheet(f"font-size: 14px; color: {color}; font-weight: bold; border: none;")
            self.setStyleSheet(f"""
                MiniStatusCard {{
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    border-left: 3px solid {color};
                }}
            """)

    def set_color(self, color: str):
        self._color = color
        self._value_lbl.setStyleSheet(f"font-size: 14px; color: {color}; font-weight: bold; border: none;")
        self.setStyleSheet(f"""
            MiniStatusCard {{
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                border-left: 3px solid {color};
            }}
        """)


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
    """CARIZON-模块部署工具 v2.0"""

    STATUS_COLORS = {
        DeployStatus.IDLE: "#666666",
        DeployStatus.CHECKING: "#2196F3",
        DeployStatus.TRANSFERRING: "#FF9800",
        DeployStatus.BOARD_OPERATING: "#9C27B0",
        DeployStatus.WAITING_REBOOT: "#FF5722",
        DeployStatus.SUCCESS: "#4CAF50",
        DeployStatus.FAILED: "#F44336",
        DeployStatus.ROLLING_BACK: "#FF5722",
        DeployStatus.CANCELLED: "#9E9E9E",
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

        # 全局样式
        self.setStyleSheet("""
            QMainWindow { background-color: #eef1f5; }
            QGroupBox {
                font-weight: bold; font-size: 13px;
                border: 1px solid #e4e4e4; border-radius: 6px;
                margin-top: 12px; padding-top: 14px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 12px;
                padding: 0 6px; color: #444;
            }
            QPushButton {
                padding: 5px 12px; border-radius: 5px;
                border: 1px solid #d0d0d0;
                background-color: #ffffff; min-height: 22px; font-size: 12px;
            }
            QPushButton:hover { background-color: #f0f0f0; border-color: #bbb; }
            QPushButton:pressed { background-color: #e4e4e4; }
            QPushButton:disabled { background-color: #f5f5f5; color: #bbb; border-color: #e0e0e0; }
            QLineEdit {
                padding: 4px 8px; border: 1px solid #d0d0d0;
                border-radius: 5px; background-color: #fafafa; font-size: 12px;
            }
            QLineEdit:focus { border-color: #2196F3; background-color: white; }
            QListWidget {
                border: 1px solid #e4e4e4; border-radius: 6px;
                background-color: white; font-size: 13px; padding: 2px;
            }
            QListWidget::item { padding: 5px 8px; border-radius: 4px; }
            QListWidget::item:selected { background-color: #E3F2FD; color: #1565C0; }
            QListWidget::item:hover { background-color: #f5f5f5; }
            QProgressBar {
                border: none; border-radius: 4px; text-align: center;
                height: 18px; background-color: #e8e8e8;
                font-size: 11px; font-weight: bold; color: #444;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3, stop:1 #42A5F5);
                border-radius: 4px;
            }
            QTextEdit {
                border: 1px solid #e4e4e4; border-radius: 6px;
                background-color: #1a1a2e; color: #e0e0e0;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px; padding: 8px;
            }
            QTableWidget {
                border: 1px solid #e4e4e4; border-radius: 6px;
                background-color: white; gridline-color: #f0f0f0;
                font-size: 12px;
            }
            QTableWidget::item { padding: 3px 5px; }
            QHeaderView::section {
                background-color: #f5f5f5; border: none;
                border-bottom: 1px solid #e0e0e0; padding: 4px 6px;
                font-weight: bold; font-size: 11px; color: #555;
            }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #ccc; border-radius: 3px; min-height: 25px; }
            QScrollBar::handle:vertical:hover { background: #aaa; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QComboBox {
                padding: 3px 6px; border: 1px solid #d0d0d0;
                border-radius: 4px; background: white; font-size: 12px;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 8, 12, 8)

        # ====== 顶部导航栏（仅状态信息） ======
        header = self._create_header()
        main_layout.addWidget(header)

        # ====== 核心信息栏（一行紧凑） ======
        info_row = self._create_info_row()
        main_layout.addLayout(info_row)

        # ====== 主内容区（QSplitter 可拖拽） ======
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setChildrenCollapsible(False)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e0e0e0;
                border-radius: 3px;
                margin: 4px 0;
            }
            QSplitter::handle:hover {
                background-color: #2196F3;
            }
            QSplitter::handle:pressed {
                background-color: #1976D2;
            }
        """)
        left = self._create_left_panel()
        right = self._create_right_panel()
        left.setMinimumWidth(300)
        right.setMinimumWidth(400)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([480, 720])
        main_layout.addWidget(splitter, 1)

        # ====== 底部操作栏 ======
        bottom = self._create_bottom_bar()
        main_layout.addWidget(bottom)

    # ==================== 顶部导航栏 ====================

    def _create_header(self):
        h = QFrame()
        h.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a237e, stop:1 #283593);
                border-radius: 8px;
            }
        """)
        h.setFixedHeight(44)
        add_shadow(h, blur=8, offset=1, color=QColor(0, 0, 0, 35))

        layout = QHBoxLayout(h)
        layout.setContentsMargins(14, 0, 14, 0)

        # 左侧：名称 + 版本
        title = QLabel("CARIZON-模块部署工具")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: white; border: none;")
        layout.addWidget(title)

        ver = QLabel("v2.0")
        ver.setStyleSheet("font-size: 9px; color: rgba(255,255,255,0.5); background: rgba(255,255,255,0.1); padding: 1px 5px; border-radius: 4px; border: none;")
        layout.addWidget(ver)

        layout.addSpacing(20)

        # 中间：就绪状态
        self._status_indicator = QLabel("● 就绪")
        self._status_indicator.setStyleSheet("color: #81C784; font-weight: bold; font-size: 12px; border: none;")
        layout.addWidget(self._status_indicator)

        layout.addStretch()

        # 右侧：连接状态
        self._industrial_status = QLabel("● 工控机: 未连接")
        self._industrial_status.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 11px; border: none;")
        layout.addWidget(self._industrial_status)

        self._board_status = QLabel("● 板端: 未连接")
        self._board_status.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 11px; border: none;")
        layout.addWidget(self._board_status)

        return h

    # ==================== 核心信息栏（均衡布局） ====================

    def _create_info_row(self):
        """一行布局：升级包 + 进度 + 状态 + 运行时间，宽度均衡"""
        row = QHBoxLayout()
        row.setSpacing(8)
        row.setContentsMargins(0, 0, 0, 0)

        # 升级包 - 蓝色
        self._card_packages = MiniStatusCard("升级包", "0 个", "#2196F3")
        row.addWidget(self._card_packages, 1)

        # 部署进度 - 橙色
        self._card_progress = MiniStatusCard("部署进度", "0%", "#FF9800")
        row.addWidget(self._card_progress, 1)

        # 当前状态 - 紫色，品牌色突出
        self._card_status = MiniStatusCard("当前状态", "等待开始", "#7B1FA2")
        self._card_status._value_lbl.setStyleSheet("font-size: 15px; color: #7B1FA2; font-weight: bold; border: none;")
        row.addWidget(self._card_status, 1)

        # 运行时间 - 蓝灰色，与前三者同宽
        self._card_time_card = MiniStatusCard("运行时间", "--:--:--", "#546E7A")
        row.addWidget(self._card_time_card, 1)

        return row

    # ==================== 左侧面板（40%） ====================

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ---- 升级包选择 ----
        fg = QFrame()
        fg.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e4e4e4;
                border-radius: 6px;
            }
        """)
        fl = QVBoxLayout(fg)
        fl.setSpacing(6)
        fl.setContentsMargins(10, 10, 10, 8)

        title1 = QLabel("📁 升级包选择")
        title1.setStyleSheet("font-size: 14px; color: #1565C0; font-weight: bold; border: none; padding-bottom: 4px;")
        fl.addWidget(title1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._select_btn = QPushButton("📂 选择文件")
        self._select_btn.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD; color: #1565C0;
                border: 1px solid #90CAF9; font-weight: bold;
                padding: 7px 16px; font-size: 13px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #BBDEFB; }
        """)
        self._select_btn.clicked.connect(self._select_files)
        btn_row.addWidget(self._select_btn)

        self._clear_btn = QPushButton("🗑 清空")
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFF3E0; color: #E65100;
                border: 1px solid #FFCC80; padding: 7px 16px;
                font-size: 13px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #FFE0B2; }
        """)
        self._clear_btn.clicked.connect(self._clear_files)
        btn_row.addWidget(self._clear_btn)

        btn_row.addStretch()

        fl.addLayout(btn_row)

        self._file_list = DropFileList()
        self._file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._file_list.setMinimumHeight(90)
        self._file_list.setAlternatingRowColors(True)
        self._file_list.setStyleSheet("""
            QListWidget {
                alternate-background-color: #fafafa;
                font-size: 14px; padding: 3px;
            }
            QListWidget::item { padding: 6px 10px; border-radius: 4px; }
        """)
        self._file_list.filesDropped.connect(self._on_files_dropped)
        fl.addWidget(self._file_list, 1)

        self._pkg_summary = QLabel("")
        self._pkg_summary.setStyleSheet("color: #666; font-size: 13px; padding: 2px 4px;")
        self._pkg_summary.setWordWrap(True)
        fl.addWidget(self._pkg_summary)

        layout.addWidget(fg, 2)

        # ---- 部署进度 ----
        pg = QFrame()
        pg.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e4e4e4;
                border-radius: 6px;
            }
        """)
        pl = QVBoxLayout(pg)
        pl.setSpacing(6)
        pl.setContentsMargins(10, 10, 10, 8)

        title2 = QLabel("📊 部署进度")
        title2.setStyleSheet("font-size: 14px; color: #E65100; font-weight: bold; border: none; padding-bottom: 4px;")
        pl.addWidget(title2)

        pbar = QHBoxLayout()
        self._progress_bar = QProgressBar()
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("  %p%  -  当前包: %v/%m ")
        self._progress_bar.setFixedHeight(22)
        pbar.addWidget(self._progress_bar, 1)

        self._progress_pct = QLabel("0%")
        self._progress_pct.setStyleSheet("font-size: 18px; font-weight: bold; color: #E65100;")
        self._progress_pct.setFixedWidth(46)
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
        self._pkg_table.setStyleSheet("""
            QTableWidget { font-size: 13px; border-radius: 6px; }
            QTableWidget::item { padding: 4px 6px; }
        """)
        pl.addWidget(self._pkg_table)

        layout.addWidget(pg, 3)
        return panel

    # ==================== 右侧面板（60%） ====================

    def _create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        lg = QFrame()
        lg.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e4e4e4;
                border-radius: 6px;
            }
        """)
        ll = QVBoxLayout(lg)
        ll.setSpacing(6)
        ll.setContentsMargins(10, 10, 10, 8)

        title3 = QLabel("📝 实时日志")
        title3.setStyleSheet("font-size: 14px; color: #1a1a2e; font-weight: bold; border: none; padding-bottom: 4px;")
        ll.addWidget(title3)

        # 工具栏
        tb = QHBoxLayout()
        tb.setSpacing(6)

        fl = QLabel("过滤:")
        fl.setStyleSheet("font-size: 13px; color: #555;")
        tb.addWidget(fl)

        self._log_filter_combo = QComboBox()
        self._log_filter_combo.addItems(["全部", "INFO", "WARN", "ERROR"])
        self._log_filter_combo.setFixedWidth(75)
        tb.addWidget(self._log_filter_combo)

        self._log_search_edit = QLineEdit()
        self._log_search_edit.setPlaceholderText("🔍 搜索日志...")
        self._log_search_edit.setStyleSheet("font-size: 13px; padding: 5px 8px;")
        self._log_search_edit.returnPressed.connect(self._filter_logs)
        tb.addWidget(self._log_search_edit, 1)

        self._log_clear_btn = QPushButton("清空")
        self._log_clear_btn.setFixedWidth(55)
        self._log_clear_btn.setStyleSheet("font-size: 12px; padding: 4px 10px;")
        self._log_clear_btn.clicked.connect(self._clear_logs)
        tb.addWidget(self._log_clear_btn)

        ll.addLayout(tb)

        self._log_output = QTextEdit()
        self._log_output.setReadOnly(True)
        self._log_output.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e4e4e4; border-radius: 6px;
                background-color: #1a1a2e; color: #e0e0e0;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px; padding: 10px;
            }
        """)
        ll.addWidget(self._log_output, 1)

        layout.addWidget(lg, 1)
        return panel

    # ==================== 底部操作栏 ====================

    def _create_bottom_bar(self):
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e4e4e4;
                border-radius: 8px;
            }
        """)
        bar.setFixedHeight(48)
        add_shadow(bar, blur=6, offset=1, color=QColor(0, 0, 0, 15))

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # 左侧：版本信息
        ver_label = QLabel("CARIZON-模块部署工具  v2.0")
        ver_label.setStyleSheet("font-size: 11px; color: #999; border: none;")
        layout.addWidget(ver_label)

        layout.addStretch()

        # 功能按钮组（浅灰色）
        self._settings_btn = QPushButton("⚙ 配置")
        self._settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5; color: #555;
                border: 1px solid #ddd; font-size: 12px;
                padding: 5px 14px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #eee; }
        """)
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)

        self._log_btn = QPushButton("📋 日志查看器")
        self._log_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5; color: #555;
                border: 1px solid #ddd; font-size: 12px;
                padding: 5px 14px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #eee; }
        """)
        self._log_btn.clicked.connect(self._open_log_viewer)
        layout.addWidget(self._log_btn)

        # 分隔
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("border: none; border-left: 1px solid #e0e0e0;")
        sep.setFixedWidth(1)
        layout.addWidget(sep)

        # 操作按钮组（绿色/红色）
        self._deploy_btn = QPushButton("▶ 部署")
        self._deploy_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50; color: white; border: none;
                font-weight: bold; font-size: 13px; padding: 6px 24px; border-radius: 5px;
            }
            QPushButton:hover { background: #43A047; }
            QPushButton:disabled { background: #A5D6A7; color: rgba(255,255,255,0.6); }
        """)
        self._deploy_btn.clicked.connect(self._start_deploy)
        layout.addWidget(self._deploy_btn)

        self._stop_btn = QPushButton("⏹ 停止")
        self._stop_btn.setStyleSheet("""
            QPushButton {
                background: #F44336; color: white; border: none;
                font-weight: bold; font-size: 13px; padding: 6px 20px; border-radius: 5px;
            }
            QPushButton:hover { background: #D32F2F; }
            QPushButton:disabled { background: #EF9A9A; color: rgba(255,255,255,0.6); }
        """)
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
                item.setForeground(QColor("#1B5E20"))
                item.setData(Qt.UserRole, pi.pkg_type)
            else:
                item.setText(f"  {fn}  [⚠]")
                item.setForeground(QColor("#B71C1C"))
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
            si.setForeground(QColor("#999"))
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
            self._pkg_table.item(i, 2).setForeground(QColor("#999"))

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
        color = self.STATUS_COLORS.get(status, "#666666")
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
        self._status_indicator.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px; border: none;")

        # 卡片状态
        sc = {
            DeployStatus.SUCCESS: "#4CAF50", DeployStatus.FAILED: "#F44336",
            DeployStatus.CHECKING: "#2196F3", DeployStatus.TRANSFERRING: "#FF9800",
            DeployStatus.BOARD_OPERATING: "#9C27B0", DeployStatus.WAITING_REBOOT: "#FF5722",
            DeployStatus.ROLLING_BACK: "#FF5722", DeployStatus.CANCELLED: "#9E9E9E",
        }
        self._card_status.set_value(name)
        self._card_status.set_color(sc.get(status, "#666666"))

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
                self._flash_animation("#4CAF50")
                QMessageBox.information(self, "🎉 部署完成", "所有包部署成功！")
            elif status == DeployStatus.FAILED:
                self._flash_animation("#F44336")
                QMessageBox.critical(self, "❌ 部署失败", f"部署失败:\n{message}")

    def _flash_animation(self, color: str):
        for i in range(3):
            QTimer.singleShot(i * 300, lambda c=color: self._status_indicator.setStyleSheet(
                f"color: {c}; font-weight: bold; font-size: 15px; border: none;"))
            QTimer.singleShot(i * 300 + 150, lambda c=color: self._status_indicator.setStyleSheet(
                f"color: {c}; font-weight: bold; font-size: 12px; border: none;"))

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

        cm = {"INFO": "#81C784", "WARN": "#FFB74D", "WARNING": "#FFB74D",
              "ERROR": "#E57373", "DEBUG": "#90A4AE"}
        color = cm.get(level.upper(), "#e0e0e0")
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
            self._board_status.setStyleSheet("color: #81C784; font-size: 11px; border: none;")
        if config.get("工控机_IP"):
            self._industrial_status.setText(f"● 工控机: {config.get('工控机_IP')}")
            self._industrial_status.setStyleSheet("color: #81C784; font-size: 11px; border: none;")

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
