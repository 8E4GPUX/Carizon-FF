"""
SSH 客户端单元测试
"""
import sys
import os
import pytest

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from core.ssh_client import SSHClient, set_error_keywords, ERROR_KEYWORDS


class TestSSHClientInit:
    """SSHClient 初始化测试"""

    def test_init_with_minimal_params(self):
        """测试最小参数初始化"""
        client = SSHClient("192.168.1.1", "root")
        assert client.hostname == "192.168.1.1"
        assert client.username == "root"
        assert client.password is None
        assert client.port == 22
        assert client.timeout == 8
        assert client.max_retry == 3
        assert client.key_file is None

    def test_init_with_all_params(self):
        """测试完整参数初始化"""
        client = SSHClient(
            hostname="192.168.1.1",
            username="admin",
            password="secret",
            port=2222,
            timeout=15,
            retry=5,
            key_file="/path/to/key",
        )
        assert client.hostname == "192.168.1.1"
        assert client.username == "admin"
        assert client.password == "secret"
        assert client.port == 2222
        assert client.timeout == 15
        assert client.max_retry == 5
        assert client.key_file == "/path/to/key"

    def test_init_default_port(self):
        """测试默认端口"""
        client = SSHClient("host", "user")
        assert client.port == 22

    def test_init_default_timeout(self):
        """测试默认超时"""
        client = SSHClient("host", "user")
        assert client.timeout == 8

    def test_init_default_retry(self):
        """测试默认重试次数"""
        client = SSHClient("host", "user")
        assert client.max_retry == 3


class TestSetErrorKeywords:
    """set_error_keywords 测试"""

    def test_set_error_keywords(self):
        """测试设置错误关键词"""
        keywords = ["错误1", "错误2"]
        set_error_keywords(keywords)
        assert ERROR_KEYWORDS == keywords

    def test_set_empty_keywords(self):
        """测试设置空关键词列表"""
        set_error_keywords([])
        assert ERROR_KEYWORDS == []

    def test_set_keywords_override(self):
        """测试关键词覆盖"""
        set_error_keywords(["旧关键词"])
        set_error_keywords(["新关键词"])
        assert ERROR_KEYWORDS == ["新关键词"]


class TestSSHClientDisconnected:
    """SSHClient 未连接状态测试"""

    @pytest.fixture
    def client(self):
        set_error_keywords([])
        return SSHClient("192.168.1.1", "root", timeout=3, retry=1)

    def test_is_connected_when_not_connected(self, client):
        """测试未连接时 is_connected 返回 False"""
        assert client.is_connected() is False

    def test_connect_to_unreachable_host(self, client):
        """测试连接不可达主机"""
        result = client.connect()
        assert result is False

    def test_disconnect_when_not_connected(self, client):
        """测试未连接时断开不报错"""
        client.disconnect()  # 不应抛出异常

    def test_ensure_connected_when_not_connected(self, client):
        """测试未连接时 ensure_connected"""
        result = client.ensure_connected()
        assert result is False

    def test_exec_command_when_not_connected(self, client):
        """测试未连接时执行命令"""
        success, out, err = client.exec_command("echo hello")
        assert success is False
        assert "SSH 连接失败" in err

    def test_get_sftp_when_not_connected(self, client):
        """测试未连接时获取 SFTP"""
        sftp = client.get_sftp()
        assert sftp is None

    def test_check_remote_path_when_not_connected(self, client):
        """测试未连接时检查远程路径"""
        result = client.check_remote_path_exists("/test")
        assert result is False

    def test_get_remote_disk_space_when_not_connected(self, client):
        """测试未连接时获取磁盘空间"""
        space = client.get_remote_disk_space_kb("/ota")
        assert space == 0

    def test_get_remote_file_size_when_not_connected(self, client):
        """测试未连接时获取文件大小"""
        size = client.get_remote_file_size_kb("/test.zip")
        assert size == 0

    def test_test_connectivity_when_not_connected(self, client):
        """测试未连接时连通性检测"""
        result = client.test_connectivity()
        assert result is False
