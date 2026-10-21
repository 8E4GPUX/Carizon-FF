"""
部署历史查看对话框
展示最近部署记录，支持查看详情
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLabel, QAbstractItemView, QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from core.deploy_history import DeployHistory


class HistoryDialog(QDialog):
    """部署历史查看对话框"""

    STATUS_COLORS = {
        "success": "#4CAF50",
        "failed": "#F44336",
        "cancelled": "#999999",
        "running": "#FF9800",
    }
    STATUS_NAMES = {
        "success": "成功",
        "failed": "失败",
        "cancelled": "已取消",
        "running": "进行中",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("部署历史")
        self.resize(760, 460)
        self._history = DeployHistory()
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title = QLabel("最近部署记录（点击行查看详情）")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["开始时间", "状态", "包数", "耗时", "设备 IP"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.setColumnWidth(1, 70)
        self._table.setColumnWidth(2, 50)
        self._table.setColumnWidth(3, 70)
        self._table.setColumnWidth(4, 120)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.cellDoubleClicked.connect(self._show_detail)
        layout.addWidget(self._table, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.clicked.connect(self._load_data)
        btn_row.addWidget(self._refresh_btn)
        self._close_btn = QPushButton("关闭")
        self._close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._close_btn)
        layout.addLayout(btn_row)

    def _load_data(self):
        """加载并展示历史记录"""
        records = self._history.get_recent_records(50)
        self._table.setRowCount(len(records))
        for i, r in enumerate(records):
            time_item = QTableWidgetItem(r["start_time"])
            status_item = QTableWidgetItem(
                self.STATUS_NAMES.get(r["status"], r["status"]))
            color = self.STATUS_COLORS.get(r["status"], "#333333")
            status_item.setForeground(QColor(color))
            status_item.setTextAlignment(Qt.AlignCenter)

            pkg_count = QTableWidgetItem(str(r["package_count"]))
            pkg_count.setTextAlignment(Qt.AlignCenter)

            dur = r["total_duration_sec"]
            dur_item = QTableWidgetItem(
                f"{dur:.0f}s" if dur else "-")
            dur_item.setTextAlignment(Qt.AlignCenter)

            ip_item = QTableWidgetItem(r["device_ip"] or "-")
            ip_item.setTextAlignment(Qt.AlignCenter)

            self._table.setItem(i, 0, time_item)
            self._table.setItem(i, 1, status_item)
            self._table.setItem(i, 2, pkg_count)
            self._table.setItem(i, 3, dur_item)
            self._table.setItem(i, 4, ip_item)

    def refresh(self):
        """刷新数据（窗口重新显示时调用）"""
        self._load_data()

    def _show_detail(self, row, _col):
        """显示记录详情"""
        record_id = self._history.get_recent_records(50)[row]["id"]
        detail = self._history.get_record_detail(record_id)
        if not detail:
            return

        packages = detail.get("packages_detail", [])
        pkg_lines = "\n".join(
            f"  • {p['package_name']}  [{self.STATUS_NAMES.get(p['status'], p['status'])}]"
            for p in packages
        ) or "  （无）"

        msg = (
            f"开始时间: {detail.get('start_time', '-')}\n"
            f"结束时间: {detail.get('end_time', '-')}\n"
            f"状态: {self.STATUS_NAMES.get(detail.get('status', ''), detail.get('status', '-'))}\n"
            f"设备 IP: {detail.get('device_ip') or '-'}\n"
            f"总耗时: {detail.get('total_duration_sec') or '-'} 秒\n"
            f"错误信息: {detail.get('error_message') or '无'}\n\n"
            f"升级包:\n{pkg_lines}"
        )
        QMessageBox.information(self, f"部署记录 #{record_id}", msg)
