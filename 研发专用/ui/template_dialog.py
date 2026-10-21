"""
模板管理对话框
查看、删除、导入、导出部署模板
"""
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFileDialog, QMessageBox, QAbstractItemView,
)
from PyQt5.QtCore import Qt

from core.template_manager import TemplateManager, DeployTemplate


class TemplateDialog(QDialog):
    """模板管理对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模板管理")
        self.resize(520, 420)
        self._tpl_mgr = TemplateManager()
        self._init_ui()
        self._load_templates()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title = QLabel("已保存的部署模板")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self._list, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._delete_btn = QPushButton("删除")
        self._delete_btn.clicked.connect(self._delete_template)
        btn_row.addWidget(self._delete_btn)

        self._export_btn = QPushButton("导出")
        self._export_btn.clicked.connect(self._export_template)
        btn_row.addWidget(self._export_btn)

        self._import_btn = QPushButton("导入")
        self._import_btn.clicked.connect(self._import_template)
        btn_row.addWidget(self._import_btn)

        btn_row.addStretch()

        self._close_btn = QPushButton("关闭")
        self._close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._close_btn)

        layout.addLayout(btn_row)

    def _load_templates(self):
        """加载模板列表"""
        self._list.clear()
        templates = self._tpl_mgr.list_templates()
        if not templates:
            item = QListWidgetItem("（暂无模板）")
            item.setEnabled(False)
            self._list.addItem(item)
            return
        for t in templates:
            pkg_desc = f"{len(t.packages)} 个包" if t.packages else "无包"
            item = QListWidgetItem(f"{t.name}  —  {pkg_desc}")
            item.setData(Qt.UserRole, t.name)
            self._list.addItem(item)

    def refresh(self):
        """刷新数据（窗口重新显示时调用）"""
        self._load_templates()

    def _selected_name(self) -> str:
        item = self._list.currentItem()
        if item is None:
            return ""
        return item.data(Qt.UserRole) or ""

    def _delete_template(self):
        name = self._selected_name()
        if not name:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return
        ret = QMessageBox.question(
            self, "确认删除", f"确定删除模板 [{name}] 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        if self._tpl_mgr.delete(name):
            QMessageBox.information(self, "成功", f"模板 [{name}] 已删除")
            self._load_templates()
        else:
            QMessageBox.critical(self, "失败", "删除模板失败")

    def _export_template(self):
        name = self._selected_name()
        if not name:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出模板", f"{name}.json", "JSON 文件 (*.json)")
        if not path:
            return
        if self._tpl_mgr.export_template(name, path):
            QMessageBox.information(self, "成功", f"已导出到:\n{path}")
        else:
            QMessageBox.critical(self, "失败", "导出模板失败")

    def _import_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入模板", "", "JSON 文件 (*.json)")
        if not path:
            return
        if self._tpl_mgr.import_template(path):
            QMessageBox.information(self, "成功", "模板导入成功")
            self._load_templates()
        else:
            QMessageBox.critical(self, "失败", "导入模板失败")
