"""
包分类器模块
根据文件名关键字识别包类型和目标目录
"""
import json
import os
from config.config_manager import load_package_mapping
from utils.logger import get_logger

logger = get_logger()


class PackageInfo:
    """包信息"""

    def __init__(self, filename: str, pkg_type: str = "unknown",
                 target_dir: str = "unknown"):
        self.filename = filename
        self.pkg_type = pkg_type
        self.target_dir = target_dir

    @property
    def is_known(self) -> bool:
        return self.pkg_type != "unknown"

    def __repr__(self):
        return f"PackageInfo({self.filename}, type={self.pkg_type}, target={self.target_dir})"


class PackageClassifier:
    """包分类器，根据文件名关键字识别包类型"""

    def __init__(self, mapping_data: dict = None):
        if mapping_data is None:
            mapping_data = load_package_mapping()
        self._mapping = mapping_data.get("keyword_mapping", [])
        self._error_keywords = mapping_data.get("error_keywords", [])
        self._cleanup_paths = mapping_data.get("default_cleanup_paths", [])

    def classify(self, filename: str) -> PackageInfo:
        """根据文件名分类包

        Args:
            filename: 文件名（含扩展名）

        Returns:
            PackageInfo 对象
        """
        lower_name = filename.lower()

        for rule in self._mapping:
            keyword = rule["keyword"].lower()
            if keyword in lower_name:
                return PackageInfo(
                    filename=filename,
                    pkg_type=rule["type"],
                    target_dir=rule.get("target_dir", ""),
                )

        return PackageInfo(filename=filename)

    def classify_batch(self, filenames: list) -> list:
        """批量分类

        Args:
            filenames: 文件名列表

        Returns:
            PackageInfo 列表
        """
        return [self.classify(f) for f in filenames]

    @property
    def error_keywords(self) -> list:
        return self._error_keywords

    @property
    def cleanup_paths(self) -> list:
        return self._cleanup_paths
