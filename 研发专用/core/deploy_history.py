"""
部署历史记录模块
使用 SQLite 存储部署历史，提供统计分析和报告导出
"""
import os
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger()

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "deploy_history.db")


def _get_connection():
    """获取数据库连接（线程本地）"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


class DeployHistory:
    """部署历史管理器（单例）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._conn = _get_connection()
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS deploy_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                package_count INTEGER DEFAULT 0,
                packages TEXT,
                total_duration_sec REAL,
                error_message TEXT,
                operator TEXT,
                template_name TEXT,
                device_ip TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS deploy_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                package_name TEXT NOT NULL,
                package_type TEXT,
                target_dir TEXT,
                status TEXT DEFAULT 'pending',
                duration_sec REAL,
                error_message TEXT,
                FOREIGN KEY (record_id) REFERENCES deploy_records(id)
            );

            CREATE INDEX IF NOT EXISTS idx_records_start ON deploy_records(start_time DESC);
            CREATE INDEX IF NOT EXISTS idx_records_status ON deploy_records(status);
            CREATE INDEX IF NOT EXISTS idx_packages_record ON deploy_packages(record_id);
        """)
        self._conn.commit()

    def start_record(self, packages: list, operator: str = "",
                     template_name: str = "", device_ip: str = "") -> int:
        """开始记录一次部署

        Args:
            packages: 包名列表
            operator: 操作人
            template_name: 使用的模板名
            device_ip: 设备 IP

        Returns:
            记录 ID
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self._conn.execute(
            """INSERT INTO deploy_records
               (start_time, status, package_count, packages, operator, template_name, device_ip)
               VALUES (?, 'running', ?, ?, ?, ?, ?)""",
            (now, len(packages), json.dumps(packages, ensure_ascii=False),
             operator, template_name, device_ip)
        )
        record_id = cursor.lastrowid

        # 记录每个包
        for pkg in packages:
            self._conn.execute(
                """INSERT INTO deploy_packages (record_id, package_name)
                   VALUES (?, ?)""",
                (record_id, pkg)
            )
        self._conn.commit()
        logger.info(f"部署记录已创建: ID={record_id}, 包数={len(packages)}")
        return record_id

    def update_package_status(self, record_id: int, package_name: str,
                               status: str, duration_sec: float = 0,
                               error: str = ""):
        """更新单个包的状态"""
        self._conn.execute(
            """UPDATE deploy_packages SET status=?, duration_sec=?, error_message=?
               WHERE record_id=? AND package_name=?""",
            (status, duration_sec, error, record_id, package_name)
        )
        self._conn.commit()

    def finish_record(self, record_id: int, status: str,
                      error_message: str = ""):
        """完成部署记录"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 计算总耗时
        cursor = self._conn.execute(
            "SELECT start_time FROM deploy_records WHERE id=?", (record_id,)
        )
        row = cursor.fetchone()
        duration = 0
        if row:
            start = datetime.strptime(row["start_time"], "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
            duration = (end - start).total_seconds()

        self._conn.execute(
            """UPDATE deploy_records
               SET end_time=?, status=?, total_duration_sec=?, error_message=?
               WHERE id=?""",
            (now, status, duration, error_message, record_id)
        )
        self._conn.commit()
        logger.info(f"部署记录已完成: ID={record_id}, 状态={status}, 耗时={duration:.1f}s")

    def get_recent_records(self, limit: int = 50) -> list:
        """获取最近的部署记录"""
        cursor = self._conn.execute(
            """SELECT * FROM deploy_records
               ORDER BY start_time DESC LIMIT ?""",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_record_detail(self, record_id: int) -> dict:
        """获取部署记录详情"""
        cursor = self._conn.execute(
            "SELECT * FROM deploy_records WHERE id=?", (record_id,)
        )
        record = cursor.fetchone()
        if not record:
            return {}
        result = dict(record)

        cursor = self._conn.execute(
            "SELECT * FROM deploy_packages WHERE record_id=?", (record_id,)
        )
        result["packages_detail"] = [dict(row) for row in cursor.fetchall()]
        return result

    def get_statistics(self, days: int = 30) -> dict:
        """获取统计信息

        Args:
            days: 统计天数

        Returns:
            统计字典
        """
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        # 总部署次数
        total = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM deploy_records WHERE start_time >= ?",
            (since,)
        ).fetchone()["cnt"]

        # 成功/失败统计
        status_stats = self._conn.execute(
            """SELECT status, COUNT(*) as cnt FROM deploy_records
               WHERE start_time >= ? GROUP BY status""",
            (since,)
        ).fetchall()

        success = 0
        failed = 0
        for row in status_stats:
            if row["status"] == "success":
                success = row["cnt"]
            elif row["status"] == "failed":
                failed = row["cnt"]

        # 平均耗时
        avg_duration = self._conn.execute(
            """SELECT AVG(total_duration_sec) as avg_dur FROM deploy_records
               WHERE start_time >= ? AND status='success'""",
            (since,)
        ).fetchone()["avg_dur"] or 0

        # 成功率
        success_rate = (success / total * 100) if total > 0 else 0

        # 每日部署统计
        daily = self._conn.execute(
            """SELECT DATE(start_time) as day, COUNT(*) as cnt
               FROM deploy_records WHERE start_time >= ?
               GROUP BY DATE(start_time) ORDER BY day""",
            (since,)
        ).fetchall()

        # 包类型统计
        pkg_type_stats = self._conn.execute(
            """SELECT p.package_type, COUNT(*) as cnt
               FROM deploy_packages p JOIN deploy_records r ON p.record_id=r.id
               WHERE r.start_time >= ? AND p.package_type IS NOT NULL
               GROUP BY p.package_type""",
            (since,)
        ).fetchall()

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round(success_rate, 1),
            "avg_duration_sec": round(avg_duration, 1),
            "daily": [{"day": r["day"], "count": r["cnt"]} for r in daily],
            "pkg_type_stats": [{"type": r["package_type"], "count": r["cnt"]}
                               for r in pkg_type_stats],
        }

    def export_report(self, days: int = 30) -> str:
        """导出部署报告（Markdown 格式）

        Returns:
            Markdown 报告文本
        """
        stats = self.get_statistics(days)
        records = self.get_recent_records(20)

        lines = [
            "# 部署报告",
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> 统计周期: 最近 {days} 天",
            "",
            "## 概览",
            f"- 总部署次数: {stats['total']}",
            f"- 成功: {stats['success']}",
            f"- 失败: {stats['failed']}",
            f"- 成功率: {stats['success_rate']}%",
            f"- 平均耗时: {stats['avg_duration_sec']}秒",
            "",
            "## 最近部署记录",
            "| 时间 | 状态 | 包数 | 耗时 |",
            "|------|------|------|------|",
        ]
        for r in records[:20]:
            dur = f"{r['total_duration_sec']:.0f}s" if r['total_duration_sec'] else "-"
            lines.append(f"| {r['start_time']} | {r['status']} | {r['package_count']} | {dur} |")

        return "\n".join(lines)
