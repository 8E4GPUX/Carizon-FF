"""
产品需求监控窗口
每 2 分钟自动检测 产品专用/ 目录的 Git 更新，有新需求/Bug 时高亮提示
"""
import sys
import os
import subprocess
import threading
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor, QTextCursor, QTextCharFormat


# ========== Git 操作 ==========

GIT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_git_log():
    """获取 产品专用/ 目录的最新提交记录"""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-10", "--", "产品专用/"],
            cwd=GIT_DIR,
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Git 错误: {e}"


def run_git_show(commit_hash):
    """获取某次提交的详细信息"""
    try:
        result = subprocess.run(
            ["git", "show", "--stat", "--format=format:%H%n%an%n%ai%n%s%n%b", commit_hash],
            cwd=GIT_DIR,
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return ""


# ========== 信号桥接 ==========

class MonitorSignals(QObject):
    update_signal = pyqtSignal(str, str)  # (commit_hash, detail)


# ========== 监控窗口 ==========

class MonitorWindow(QMainWindow):
    """产品需求监控窗口"""

    def __init__(self):
        super().__init__()
        self._last_known_commits = set()
        self._signals = MonitorSignals()
        self._signals.update_signal.connect(self._on_new_commit)

        self._init_ui()
        self._init_monitor()

    def _init_ui(self):
        self.setWindowTitle("📡 产品需求监控器")
        self.resize(700, 500)
        self.setMinimumSize(500, 350)

        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a2e; }
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
            }
            QTextEdit {
                background-color: #16213e;
                color: #e0e0e0;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                border: 1px solid #0f3460;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton {
                padding: 6px 16px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 8, 12, 8)

        # ====== 顶部状态栏 ======
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0f3460, stop:1 #1a1a2e);
                border-radius: 8px;
                border: 1px solid #0f3460;
            }
        """)
        header.setFixedHeight(50)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 0, 14, 0)

        title = QLabel("📡 产品需求监控器")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #e94560; border: none;")
        h_layout.addWidget(title)

        h_layout.addStretch()

        self._status_label = QLabel("● 监控中")
        self._status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px; border: none;")
        h_layout.addWidget(self._status_label)

        self._time_label = QLabel("")
        self._time_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; border: none;")
        h_layout.addWidget(self._time_label)

        layout.addWidget(header)

        # ====== 信息栏 ======
        info_bar = QFrame()
        info_bar.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 6px;
            }
        """)
        info_bar.setFixedHeight(36)
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(12, 0, 12, 0)

        self._commit_count = QLabel("已检测提交: 0")
        self._commit_count.setStyleSheet("color: #2196F3; font-size: 12px; border: none;")
        info_layout.addWidget(self._commit_count)

        info_layout.addStretch()

        self._new_flag = QLabel("")
        self._new_flag.setStyleSheet("color: #e94560; font-weight: bold; font-size: 12px; border: none;")
        info_layout.addWidget(self._new_flag)

        layout.addWidget(info_bar)

        # ====== 日志显示区 ======
        self._log_output = QTextEdit()
        self._log_output.setReadOnly(True)
        layout.addWidget(self._log_output, 1)

        # ====== 底部按钮 ======
        btn_bar = QFrame()
        btn_bar.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 6px;
            }
        """)
        btn_bar.setFixedHeight(44)
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(10, 4, 10, 4)

        self._check_now_btn = QPushButton("🔄 立即检查")
        self._check_now_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; color: white;
                border: none; padding: 6px 18px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self._check_now_btn.clicked.connect(self._check_now)
        btn_layout.addWidget(self._check_now_btn)

        self._clear_btn = QPushButton("🗑 清空日志")
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242; color: #e0e0e0;
                border: 1px solid #616161; padding: 6px 14px;
            }
            QPushButton:hover { background-color: #616161; }
        """)
        self._clear_btn.clicked.connect(self._clear_log)
        btn_layout.addWidget(self._clear_btn)

        btn_layout.addStretch()

        self._auto_label = QLabel("⏱ 每 2 分钟自动检测")
        self._auto_label.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11px; border: none;")
        btn_layout.addWidget(self._auto_label)

        layout.addWidget(btn_bar)

        # 初始日志
        self._append_log("系统", "监控器已启动，每 2 分钟检测一次产品需求更新...")

    def _init_monitor(self):
        """初始化监控定时器"""
        # 先记录当前已知的提交
        log = run_git_log()
        if log:
            for line in log.split("\n"):
                if line.strip():
                    commit_hash = line.split()[0]
                    self._last_known_commits.add(commit_hash)

        self._append_log("系统", f"已记录 {len(self._last_known_commits)} 个已知提交")
        self._commit_count.setText(f"已检测提交: {len(self._last_known_commits)}")

        # 显示最近提交
        if log:
            self._append_log("系统", "最近产品提交记录:")
            for line in log.split("\n"):
                if line.strip():
                    self._append_log("提交", line.strip())

        # 启动定时器（2 分钟 = 120000 毫秒）
        self._timer = QTimer()
        self._timer.timeout.connect(self._check_updates)
        self._timer.start(120000)

        # 更新状态时间
        self._update_time()

    def _check_updates(self):
        """检查是否有新提交"""
        self._update_time()
        self._status_label.setText("● 检测中...")
        self._status_label.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 12px; border: none;")

        # 在后台线程执行 Git 操作
        thread = threading.Thread(target=self._do_check, daemon=True)
        thread.start()

    def _do_check(self):
        """后台执行 Git 检查"""
        log = run_git_log()
        if not log:
            self._signals.update_signal.emit("error", "获取 Git 日志失败")
            return

        new_commits = []
        for line in log.split("\n"):
            if line.strip():
                commit_hash = line.split()[0]
                if commit_hash not in self._last_known_commits:
                    new_commits.append(line.strip())

        if new_commits:
            for commit_line in new_commits:
                commit_hash = commit_line.split()[0]
                detail = run_git_show(commit_hash)
                self._last_known_commits.add(commit_hash)
                self._signals.update_signal.emit("new", f"{commit_line}\n{detail}")
        else:
            self._signals.update_signal.emit("ok", "")

    def _on_new_commit(self, msg_type, detail):
        """处理检测结果"""
        if msg_type == "new":
            lines = detail.split("\n")
            commit_line = lines[0]
            self._append_log("🔴 新需求", commit_line)

            # 显示详细信息
            if len(lines) > 1:
                self._append_log("   作者", lines[1] if len(lines) > 1 else "")
                self._append_log("   时间", lines[2] if len(lines) > 2 else "")
                self._append_log("   标题", lines[3] if len(lines) > 3 else "")
                if len(lines) > 4 and lines[4].strip():
                    self._append_log("   详情", lines[4].strip())

            self._new_flag.setText("🚨 有新需求！")
            self._commit_count.setText(f"已检测提交: {len(self._last_known_commits)}")
            self._status_label.setText("● 有更新")
            self._status_label.setStyleSheet("color: #e94560; font-weight: bold; font-size: 12px; border: none;")

            # 弹出提示
            QMessageBox.information(
                self, "📢 产品新需求",
                f"检测到产品专用/ 有新提交:\n\n{commit_line}\n\n请查看监控窗口了解详情。"
            )

        elif msg_type == "ok":
            self._status_label.setText("● 监控中")
            self._status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px; border: none;")
            self._new_flag.setText("")

        elif msg_type == "error":
            self._append_log("错误", detail)
            self._status_label.setText("● 异常")
            self._status_label.setStyleSheet("color: #F44336; font-weight: bold; font-size: 12px; border: none;")

    def _check_now(self):
        """立即检查"""
        self._append_log("系统", "手动触发检查...")
        self._check_updates()

    def _clear_log(self):
        """清空日志"""
        self._log_output.clear()
        self._append_log("系统", "日志已清空")

    def _update_time(self):
        """更新时间显示"""
        now = datetime.now().strftime("%H:%M:%S")
        self._time_label.setText(f"最后检测: {now}")

    def _append_log(self, tag: str, message: str):
        """追加日志（带颜色标签）"""
        cursor = self._log_output.textCursor()
        cursor.movePosition(QTextCursor.End)

        # 时间戳
        time_fmt = QTextCharFormat()
        time_fmt.setForeground(QColor(128, 128, 128))
        timestamp = datetime.now().strftime("%H:%M:%S")
        cursor.insertText(f"[{timestamp}] ", time_fmt)

        # 标签
        tag_colors = {
            "系统": QColor(100, 200, 255),
            "提交": QColor(100, 200, 100),
            "🔴 新需求": QColor(233, 69, 96),
            "   作者": QColor(200, 180, 100),
            "   时间": QColor(180, 180, 180),
            "   标题": QColor(255, 200, 100),
            "   详情": QColor(200, 200, 200),
            "错误": QColor(255, 80, 80),
        }
        tag_fmt = QTextCharFormat()
        tag_fmt.setForeground(tag_colors.get(tag, QColor(200, 200, 200)))
        tag_fmt.setFontWeight(QFont.Bold)
        cursor.insertText(f"{tag} ", tag_fmt)

        # 消息
        msg_fmt = QTextCharFormat()
        msg_fmt.setForeground(QColor(224, 224, 224))
        cursor.insertText(f"{message}\n", msg_fmt)

        # 滚动到底部
        scrollbar = self._log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        """关闭窗口时停止定时器"""
        if hasattr(self, '_timer'):
            self._timer.stop()
        super().closeEvent(event)


# ========== 启动入口 ==========

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("产品需求监控器")
    app.setOrganizationName("CARIZON")

    window = MonitorWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
