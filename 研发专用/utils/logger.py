"""
日志工具模块
提供统一的日志记录功能，支持文件日志和控制台日志
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime


class LoggerManager:
    """日志管理器，单例模式"""

    _instance = None
    _log_dir = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init(self, log_dir: str = None, log_prefix: str = "deploy"):
        """初始化日志管理器

        Args:
            log_dir: 日志文件目录，默认在工具目录下创建 logs 文件夹
            log_prefix: 日志文件名前缀，默认 "deploy"
        """
        if self._logger is not None:
            return self._logger

        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        self._log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f"{log_prefix}_{datetime.now().strftime('%Y%m%d')}.log")

        self._logger = logging.getLogger("OTADeploy")
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()

        # 文件处理器 - 按大小轮转，最大 10MB，保留 10 个备份
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=10, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-5s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        self._logger.addHandler(file_handler)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-5s | %(message)s",
            datefmt="%H:%M:%S",
        )
        console_handler.setFormatter(console_fmt)
        self._logger.addHandler(console_handler)

        return self._logger

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            self.init()
        return self._logger

    @property
    def log_dir(self) -> str:
        return self._log_dir

    def get_log_files(self) -> list:
        """获取所有日志文件列表（按修改时间排序）"""
        if not self._log_dir or not os.path.exists(self._log_dir):
            return []
        files = [
            os.path.join(self._log_dir, f)
            for f in os.listdir(self._log_dir)
            if f.endswith(".log")
        ]
        files.sort(key=os.path.getmtime, reverse=True)
        return files


def get_logger() -> logging.Logger:
    """获取全局日志器"""
    return LoggerManager().logger
