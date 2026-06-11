"""
包完整性校验模块 - 支持 MD5/SHA256 校验
"""
import hashlib
import os
from utils.logger import get_logger

logger = get_logger()


def compute_md5(file_path: str) -> str:
    """计算文件 MD5 哈希值

    Args:
        file_path: 文件路径

    Returns:
        MD5 十六进制字符串
    """
    try:
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception as e:
        logger.error(f"计算 MD5 失败: {e}")
        return ""


def compute_sha256(file_path: str) -> str:
    """计算文件 SHA256 哈希值"""
    try:
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()
    except Exception as e:
        logger.error(f"计算 SHA256 失败: {e}")
        return ""


def verify_checksum(file_path: str, expected_hash: str,
                    algorithm: str = "md5") -> bool:
    """校验文件完整性

    Args:
        file_path: 文件路径
        expected_hash: 期望的哈希值
        algorithm: 算法 (md5/sha256)

    Returns:
        是否匹配
    """
    if algorithm == "sha256":
        actual = compute_sha256(file_path)
    else:
        actual = compute_md5(file_path)

    if not actual:
        return False

    match = actual.lower() == expected_hash.lower()
    if match:
        logger.info(f"文件校验通过: {os.path.basename(file_path)} ({algorithm})")
    else:
        logger.warning(f"文件校验失败: {os.path.basename(file_path)} "
                       f"期望={expected_hash[:16]}... 实际={actual[:16]}...")
    return match


def get_file_info(file_path: str) -> dict:
    """获取文件信息（大小、哈希值等）

    Returns:
        文件信息字典
    """
    if not os.path.exists(file_path):
        return {}

    stat = os.stat(file_path)
    return {
        "filename": os.path.basename(file_path),
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "md5": compute_md5(file_path),
        "sha256": compute_sha256(file_path),
        "modified": stat.st_mtime,
    }
