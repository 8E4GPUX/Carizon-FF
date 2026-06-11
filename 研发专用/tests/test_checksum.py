"""
包校验单元测试
"""
import sys
import os
import tempfile
import pytest

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from utils.checksum import compute_md5, compute_sha256, verify_checksum, get_file_info


class TestChecksum:
    """校验工具单元测试"""

    @pytest.fixture
    def test_file(self):
        """创建测试文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, OTA Deploy Tool!")
            path = f.name
        yield path
        os.unlink(path)

    def test_compute_md5(self, test_file):
        """测试 MD5 计算"""
        result = compute_md5(test_file)
        assert len(result) == 32
        assert all(c in "0123456789abcdef" for c in result)

    def test_compute_sha256(self, test_file):
        """测试 SHA256 计算"""
        result = compute_sha256(test_file)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_verify_checksum_match(self, test_file):
        """测试校验匹配"""
        md5 = compute_md5(test_file)
        assert verify_checksum(test_file, md5, "md5") is True

    def test_verify_checksum_mismatch(self, test_file):
        """测试校验不匹配"""
        assert verify_checksum(test_file, "00000000000000000000000000000000", "md5") is False

    def test_verify_sha256(self, test_file):
        """测试 SHA256 校验"""
        sha = compute_sha256(test_file)
        assert verify_checksum(test_file, sha, "sha256") is True

    def test_get_file_info(self, test_file):
        """测试获取文件信息"""
        info = get_file_info(test_file)
        assert info["filename"].endswith(".txt")
        assert info["size_bytes"] > 0
        assert len(info["md5"]) == 32
        assert len(info["sha256"]) == 64

    def test_compute_md5_nonexistent(self):
        """测试不存在的文件"""
        assert compute_md5("nonexistent_file.zip") == ""

    def test_compute_sha256_nonexistent(self):
        """测试不存在的文件"""
        assert compute_sha256("nonexistent_file.zip") == ""

    def test_get_file_info_nonexistent(self):
        """测试不存在的文件"""
        assert get_file_info("nonexistent_file.zip") == {}

    def test_md5_consistent(self, test_file):
        """测试 MD5 一致性"""
        assert compute_md5(test_file) == compute_md5(test_file)

    def test_sha256_consistent(self, test_file):
        """测试 SHA256 一致性"""
        assert compute_sha256(test_file) == compute_sha256(test_file)
