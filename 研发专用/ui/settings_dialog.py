"""
设置对话框
允许用户查看和修改配置项
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QTabWidget, QWidget, QSpinBox, QGroupBox,
    QMessageBox, QLabel
)
from PyQt5.QtCore import Qt
from config.config_manager import ConfigManager, get_local_ip, resolve_target_ip


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = ConfigManager()
        self._modified = False
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        self.setWindowTitle("工具设置")
        self.resize(520, 420)

        layout = QVBoxLayout(self)

        # 标签页
        tabs = QTabWidget()

        # ---- 连接配置 ----
        conn_tab = QWidget()
        conn_layout = QFormLayout(conn_tab)
        conn_layout.setSpacing(10)
        conn_layout.setContentsMargins(20, 20, 20, 20)

        # 工控机 IP + 自动检测按钮
        ip_row = QHBoxLayout()
        self._industrial_ip = QLineEdit()
        self._industrial_ip.setPlaceholderText("例如: 192.168.1.100")
        ip_row.addWidget(self._industrial_ip, 1)

        self._detect_industrial_btn = QPushButton("🔄 检测")
        self._detect_industrial_btn.setFixedWidth(60)
        self._detect_industrial_btn.setStyleSheet("font-size: 12px; padding: 4px 8px;")
        self._detect_industrial_btn.clicked.connect(self._detect_industrial_ip)
        ip_row.addWidget(self._detect_industrial_btn)

        conn_layout.addRow("工控机 IP:", ip_row)

        # 工控机密码（默认已填充，加密存储）
        self._industrial_pwd = QLineEdit()
        self._industrial_pwd.setEchoMode(QLineEdit.Password)
        self._industrial_pwd.setPlaceholderText("默认密码已自动填充")
        conn_layout.addRow("工控机 密码:", self._industrial_pwd)

        # 板端 IP + 自动检测按钮
        board_ip_row = QHBoxLayout()
        self._board_ip = QLineEdit()
        self._board_ip.setPlaceholderText("例如: 172.31.48.9")
        board_ip_row.addWidget(self._board_ip, 1)

        self._detect_board_btn = QPushButton("🔄 自动匹配")
        self._detect_board_btn.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD; color: #1565C0;
                border: 1px solid #90CAF9; font-weight: bold;
                padding: 4px 12px; font-size: 12px;
            }
            QPushButton:hover { background-color: #BBDEFB; }
        """)
        self._detect_board_btn.clicked.connect(self._detect_board_ip)
        board_ip_row.addWidget(self._detect_board_btn)

        conn_layout.addRow("板端 IP:", board_ip_row)

        # 本机 IP 信息提示
        self._local_ip_label = QLabel()
        self._local_ip_label.setStyleSheet("color: #666; font-size: 12px; padding: 4px;")
        conn_layout.addRow("", self._local_ip_label)

        tabs.addTab(conn_tab, "连接配置")

        # ---- 目录配置 ----
        dir_tab = QWidget()
        dir_layout = QFormLayout(dir_tab)
        dir_layout.setSpacing(10)
        dir_layout.setContentsMargins(20, 20, 20, 20)

        self._ota_dir = QLineEdit()
        self._ota_dir.setPlaceholderText("默认: /ota")
        dir_layout.addRow("板端 OTA 目录:", self._ota_dir)

        self._app_dir = QLineEdit()
        self._app_dir.setPlaceholderText("默认: /app")
        dir_layout.addRow("板端 APP 目录:", self._app_dir)

        self._industrial_tmp = QLineEdit()
        self._industrial_tmp.setPlaceholderText("默认: /tmp/ota_deploy")
        dir_layout.addRow("工控机临时目录:", self._industrial_tmp)

        tabs.addTab(dir_tab, "目录配置")

        # ---- 超时配置 ----
        timeout_tab = QWidget()
        timeout_layout = QFormLayout(timeout_tab)
        timeout_layout.setSpacing(10)
        timeout_layout.setContentsMargins(20, 20, 20, 20)

        self._ssh_timeout = QSpinBox()
        self._ssh_timeout.setRange(3, 60)
        self._ssh_timeout.setSuffix(" 秒")
        timeout_layout.addRow("SSH 超时:", self._ssh_timeout)

        self._ssh_retry = QSpinBox()
        self._ssh_retry.setRange(1, 10)
        self._ssh_retry.setSuffix(" 次")
        timeout_layout.addRow("SSH 重试次数:", self._ssh_retry)

        self._offline_wait = QSpinBox()
        self._offline_wait.setRange(10, 300)
        self._offline_wait.setSuffix(" 秒")
        timeout_layout.addRow("等待离线超时:", self._offline_wait)

        self._online_wait = QSpinBox()
        self._online_wait.setRange(30, 600)
        self._online_wait.setSuffix(" 秒")
        timeout_layout.addRow("等待上线超时:", self._online_wait)

        self._extra_space = QSpinBox()
        self._extra_space.setRange(0, 1024000)
        self._extra_space.setSuffix(" KB")
        timeout_layout.addRow("额外预留空间:", self._extra_space)

        tabs.addTab(timeout_tab, "超时配置")

        layout.addWidget(tabs)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._save_btn = QPushButton("保存配置")
        self._save_btn.clicked.connect(self._save_config)
        btn_layout.addWidget(self._save_btn)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        layout.addLayout(btn_layout)

    def _load_config(self):
        """加载配置到界面"""
        self._industrial_ip.setText(self._config.get("工控机_IP", ""))
        self._industrial_pwd.setText(self._config.get("工控机_密码", ""))
        self._board_ip.setText(self._config.get("板端_IP", ""))
        self._ota_dir.setText(self._config.get("板端_OTA目录", "/ota"))
        self._app_dir.setText(self._config.get("板端_APP目录", "/app"))
        self._industrial_tmp.setText(self._config.get("工控机_临时目录", "/tmp/ota_deploy"))
        self._ssh_timeout.setValue(self._config.get("SSH_超时", 8))
        self._ssh_retry.setValue(self._config.get("SSH_重试次数", 3))
        self._offline_wait.setValue(self._config.get("重启_离线等待", 60))
        self._online_wait.setValue(self._config.get("重启_在线等待", 300))
        self._extra_space.setValue(self._config.get("额外预留空间_KB", 102400))

        # 显示本机 IP 信息
        self._update_local_ip_info()

    def _update_local_ip_info(self):
        """更新本机 IP 信息显示"""
        local_ip = get_local_ip()
        if local_ip:
            target_ip = resolve_target_ip(local_ip)
            if target_ip:
                self._local_ip_label.setText(
                    f"✅ 本机 IP: {local_ip}  →  自动匹配板端 IP: {target_ip}"
                )
                self._local_ip_label.setStyleSheet(
                    "color: #2E7D32; font-size: 12px; padding: 4px; font-weight: bold;"
                )
            else:
                self._local_ip_label.setText(
                    f"⚠️ 本机 IP: {local_ip}  (未匹配到映射表中的板端 IP)"
                )
                self._local_ip_label.setStyleSheet(
                    "color: #E65100; font-size: 12px; padding: 4px;"
                )
        else:
            self._local_ip_label.setText("❌ 未检测到本机 IP")
            self._local_ip_label.setStyleSheet(
                "color: #C62828; font-size: 12px; padding: 4px;"
            )

    def _detect_industrial_ip(self):
        """自动检测工控机本机 IP"""
        local_ip = get_local_ip()
        if local_ip:
            self._industrial_ip.setText(local_ip)
            self._config.set("工控机_IP", local_ip)
            QMessageBox.information(
                self, "检测完成",
                f"检测到本机 IP: {local_ip}\n已自动填入工控机 IP 字段。"
            )
        else:
            QMessageBox.warning(self, "检测失败", "无法获取本机 IP 地址，请手动输入。")

    def _detect_board_ip(self):
        """根据本机 IP 自动匹配板端 IP"""
        local_ip = get_local_ip()
        if not local_ip:
            QMessageBox.warning(self, "检测失败", "无法获取本机 IP 地址。")
            return

        target_ip = resolve_target_ip(local_ip)
        if target_ip:
            self._board_ip.setText(target_ip)
            self._config.set("板端_IP", target_ip)
            QMessageBox.information(
                self, "匹配成功",
                f"本机 IP: {local_ip}\n"
                f"匹配到板端 IP: {target_ip}\n\n"
                f"如需修改，请直接编辑输入框。"
            )
        else:
            QMessageBox.warning(
                self, "未匹配到映射",
                f"本机 IP: {local_ip}\n\n"
                f"未找到匹配项，请手动输入板端 IP，\n"
                f"或在 package_mapping.json 中添加映射。"
            )

    def _save_config(self):
        """保存配置（先验证再保存）"""
        self._config.set("工控机_IP", self._industrial_ip.text().strip())
        self._config.set("工控机_密码", self._industrial_pwd.text().strip())
        self._config.set("板端_IP", self._board_ip.text().strip())
        self._config.set("板端_OTA目录", self._ota_dir.text().strip() or "/ota")
        self._config.set("板端_APP目录", self._app_dir.text().strip() or "/app")
        self._config.set("工控机_临时目录", self._industrial_tmp.text().strip() or "/tmp/ota_deploy")
        self._config.set("SSH_超时", self._ssh_timeout.value())
        self._config.set("SSH_重试次数", self._ssh_retry.value())
        self._config.set("重启_离线等待", self._offline_wait.value())
        self._config.set("重启_在线等待", self._online_wait.value())
        self._config.set("额外预留空间_KB", self._extra_space.value())

        # 保存前验证配置
        is_valid, errors = self._config.validate_config()
        if not is_valid:
            error_msg = "\n".join(f"• {e}" for e in errors)
            QMessageBox.warning(
                self, "配置验证失败",
                f"以下配置项存在问题，请修正后再保存：\n\n{error_msg}"
            )
            return

        try:
            self._config.save()
            self._modified = True
            QMessageBox.information(self, "成功", "配置已保存")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")

    @property
    def is_modified(self) -> bool:
        return self._modified
