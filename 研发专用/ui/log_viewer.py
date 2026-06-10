"""
日志查看器窗口
支持时间筛选、关键词搜索、日志级别过滤
"""
import os
import re
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLineEdit, QComboBox, QDateTimeEdit, QLabel, QCheckBox,
    QFileDialog, QMessageBox, QSplitter, QListWidget, QAbstractItemView,
    QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QTextCursor, QColor, QTextCharFormat, QFont
from utils.logger import LoggerManager


class LogViewer(QDialog):
    """日志查看器对话框"""

    LEVEL_COLORS = {
        "DEBUG": QColor(128, 128, 128),
        "INFO": QColor(0, 128, 0),
        "WARNING": QColor(200, 150, 0),
        "WARN": QColor(200, 150, 0),
        "ERROR": QColor(200, 0, 0),
        "FATAL": QColor(200, 0, 0),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._log_manager = LoggerManager()
        self._all_lines = []
        self._filtered_lines = []
        self._auto_refresh = True
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_logs)
        self._refresh_timer.start(3000)  # 每 3 秒自动刷新

        self._init_ui()
        self._load_logs()

    def _init_ui(self):
        self.setWindowTitle("日志查看器")
        self.resize(1000, 700)

        layout = QVBoxLayout(self)

        # 筛选条件区域
        filter_group = QGroupBox("筛选条件")
        filter_layout = QGridLayout(filter_group)

        # 时间范围
        filter_layout.addWidget(QLabel("起始时间:"), 0, 0)
        self._start_time = QDateTimeEdit()
        self._start_time.setDateTime(datetime.now() - timedelta(hours=1))
        self._start_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self._start_time.setCalendarPopup(True)
        filter_layout.addWidget(self._start_time, 0, 1)

        filter_layout.addWidget(QLabel("结束时间:"), 0, 2)
        self._end_time = QDateTimeEdit()
        self._end_time.setDateTime(datetime.now())
        self._end_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self._end_time.setCalendarPopup(True)
        filter_layout.addWidget(self._end_time, 0, 3)

        # 日志级别
        filter_layout.addWidget(QLabel("日志级别:"), 1, 0)
        self._level_combo = QComboBox()
        self._level_combo.addItems(["全部", "DEBUG", "INFO", "WARNING", "ERROR"])
        filter_layout.addWidget(self._level_combo, 1, 1)

        # 关键词搜索
        filter_layout.addWidget(QLabel("关键词:"), 1, 2)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("输入关键词搜索...")
        self._search_input.returnPressed.connect(self._apply_filter)
        filter_layout.addWidget(self._search_input, 1, 3)

        # 按钮
        btn_layout = QHBoxLayout()
        self._filter_btn = QPushButton("应用筛选")
        self._filter_btn.clicked.connect(self._apply_filter)
        btn_layout.addWidget(self._filter_btn)

        self._reset_btn = QPushButton("重置")
        self._reset_btn.clicked.connect(self._reset_filter)
        btn_layout.addWidget(self._reset_btn)

        self._auto_refresh_cb = QCheckBox("自动刷新")
        self._auto_refresh_cb.setChecked(True)
        self._auto_refresh_cb.stateChanged.connect(
            lambda: self._refresh_timer.start(3000) if self._auto_refresh_cb.isChecked()
            else self._refresh_timer.stop()
        )
        btn_layout.addWidget(self._auto_refresh_cb)

        btn_layout.addStretch()

        self._export_btn = QPushButton("导出日志")
        self._export_btn.clicked.connect(self._export_logs)
        btn_layout.addWidget(self._export_btn)

        self._clear_btn = QPushButton("清空显示")
        self._clear_btn.clicked.connect(self._clear_display)
        btn_layout.addWidget(self._clear_btn)

        filter_layout.addLayout(btn_layout, 2, 0, 1, 4)

        layout.addWidget(filter_group)

        # 日志文件列表
        file_group = QGroupBox("日志文件")
        file_layout = QVBoxLayout(file_group)
        self._file_list = QListWidget()
        self._file_list.setMaximumHeight(80)
        self._file_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._file_list.currentRowChanged.connect(self._on_file_changed)
        file_layout.addWidget(self._file_list)
        layout.addWidget(file_group)

        # 日志内容显示
        self._log_display = QTextEdit()
        self._log_display.setReadOnly(True)
        self._log_display.setFont(QFont("Consolas", 10))
        layout.addWidget(self._log_display)

        # 状态栏
        self._status_label = QLabel("就绪")
        layout.addWidget(self._status_label)

    def _load_logs(self):
        """加载日志文件列表"""
        self._file_list.clear()
        files = self._log_manager.get_log_files()
        if not files:
            self._file_list.addItem("无日志文件")
            return

        for f in files:
            name = os.path.basename(f)
            size = os.path.getsize(f)
            size_str = f"{size / 1024:.1f}KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f}MB"
            self._file_list.addItem(f"{name} ({size_str})")

        if self._file_list.count() > 0:
            self._file_list.setCurrentRow(0)

    def _on_file_changed(self, row):
        """日志文件切换"""
        if row < 0:
            return
        self._load_file_content()
        self._apply_filter()

    def _load_file_content(self):
        """加载当前选中文件内容"""
        files = self._log_manager.get_log_files()
        if not files or self._file_list.currentRow() < 0:
            return

        file_path = files[self._file_list.currentRow()]
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self._all_lines = f.readlines()
        except Exception as e:
            self._all_lines = [f"读取日志文件失败: {e}"]
        self._filtered_lines = list(self._all_lines)

    def _apply_filter(self):
        """应用筛选条件"""
        if not self._all_lines:
            self._load_file_content()

        keyword = self._search_input.text().strip()
        level_filter = self._level_combo.currentText()
        start_dt = self._start_time.dateTime().toPyDateTime()
        end_dt = self._end_time.dateTime().toPyDateTime()

        self._filtered_lines = []
        for line in self._all_lines:
            # 时间筛选
            match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
            if match:
                try:
                    line_time = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                    if line_time < start_dt or line_time > end_dt:
                        continue
                except ValueError:
                    pass

            # 级别筛选
            if level_filter != "全部":
                level_pattern = rf"\|\s*{level_filter}\s*\|"
                if not re.search(level_pattern, line):
                    continue

            # 关键词筛选
            if keyword:
                if keyword.lower() not in line.lower():
                    continue

            self._filtered_lines.append(line)

        self._update_display()

    def _reset_filter(self):
        """重置筛选条件"""
        self._start_time.setDateTime(datetime.now() - timedelta(hours=1))
        self._end_time.setDateTime(datetime.now())
        self._level_combo.setCurrentIndex(0)
        self._search_input.clear()
        self._filtered_lines = list(self._all_lines)
        self._update_display()

    def _update_display(self):
        """更新日志显示"""
        self._log_display.clear()

        for line in self._filtered_lines:
            # 根据级别着色
            color = None
            for level, level_color in self.LEVEL_COLORS.items():
                pattern = rf"\|\s*{level}\s*\|"
                if re.search(pattern, line):
                    color = level_color
                    break

            if color:
                fmt = QTextCharFormat()
                fmt.setForeground(color)
                cursor = self._log_display.textCursor()
                cursor.movePosition(QTextCursor.End)
                cursor.insertText(line, fmt)
            else:
                self._log_display.append(line.rstrip("\n"))

        # 滚动到底部
        scrollbar = self._log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        self._status_label.setText(
            f"共 {len(self._filtered_lines)} 条日志 "
            f"(筛选自 {len(self._all_lines)} 条)"
        )

    def _refresh_logs(self):
        """自动刷新日志"""
        if not self.isVisible():
            return
        self._load_file_content()
        self._apply_filter()

    def _export_logs(self):
        """导出筛选后的日志"""
        if not self._filtered_lines:
            QMessageBox.information(self, "提示", "没有可导出的日志")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", "ota_deploy_log.txt",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(self._filtered_lines)
            QMessageBox.information(self, "成功", f"日志已导出到:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")

    def _clear_display(self):
        """清空显示（不清除文件）"""
        self._log_display.clear()
        self._all_lines = []
        self._filtered_lines = []
        self._status_label.setText("已清空")

    def closeEvent(self, event):
        """关闭时停止定时器"""
        self._refresh_timer.stop()
        super().closeEvent(event)
