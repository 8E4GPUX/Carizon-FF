"""
SSH/SFTP 客户端模块
封装 paramiko 的 SSH 和 SFTP 操作，支持连接管理、命令执行、文件传输
"""
import os
import time
import socket
import paramiko
from utils.logger import get_logger

logger = get_logger()

# 错误关键词列表（从配置加载）
ERROR_KEYWORDS = []


# ========== SSH 异常类 ==========

class SSHConnectionError(Exception):
    """SSH 连接错误基类"""
    pass


class SSHTimeoutError(SSHConnectionError):
    """连接超时"""
    def __init__(self, hostname, timeout):
        self.message = f"连接 {hostname} 超时（{timeout}秒），请检查网络连通性"
        super().__init__(self.message)


class SSHAuthError(SSHConnectionError):
    """认证失败"""
    def __init__(self, hostname, username):
        self.message = f"用户 {username}@{hostname} 认证失败，请检查密码或密钥文件"
        super().__init__(self.message)


class SSHHostUnreachableError(SSHConnectionError):
    """主机不可达"""
    def __init__(self, hostname):
        self.message = f"主机 {hostname} 不可达，请检查网络连接和 IP 地址"
        super().__init__(self.message)


def set_error_keywords(keywords: list):
    """设置错误关键词列表"""
    global ERROR_KEYWORDS
    ERROR_KEYWORDS.clear()
    ERROR_KEYWORDS.extend(keywords)


class SSHClient:
    """SSH 客户端，封装连接管理和命令执行"""

    def __init__(self, hostname: str, username: str, password: str = None,
                 port: int = 22, timeout: int = 8, retry: int = 3,
                 key_file: str = None, sock=None):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.max_retry = retry
        self.key_file = key_file
        self._sock = sock  # 跳板机隧道 socket（通过工控机连接板端）
        self._client = None
        self._sftp = None

    def connect(self) -> bool:
        """建立 SSH 连接（带重试，支持密码和密钥认证）"""
        last_error = None
        for attempt in range(1, self.max_retry + 1):
            try:
                self._client = paramiko.SSHClient()
                self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                connect_kwargs = {
                    "hostname": self.hostname,
                    "port": self.port,
                    "username": self.username,
                    "timeout": self.timeout,
                    "compress": True,
                }

                # 跳板机隧道（通过工控机连接板端）
                if self._sock is not None:
                    connect_kwargs["sock"] = self._sock

                # 优先使用密钥认证
                if self.key_file and os.path.exists(self.key_file):
                    connect_kwargs["key_filename"] = self.key_file
                    if self.password:
                        connect_kwargs["password"] = self.password
                elif self.password:
                    connect_kwargs["password"] = self.password
                # 无密码无密钥时，尝试空密码认证

                self._client.connect(**connect_kwargs)
                logger.info(f"SSH 连接成功: {self.username}@{self.hostname}:{self.port}")
                return True
            except paramiko.AuthenticationException:
                last_error = SSHAuthError(self.hostname, self.username)
                logger.warning(f"SSH 认证失败 (尝试 {attempt}/{self.max_retry}): {last_error.message}")
                if self._client:
                    self._client.close()
                    self._client = None
                if attempt < self.max_retry:
                    time.sleep(2)
            except paramiko.SSHException as e:
                msg = str(e)
                if "timeout" in msg.lower() or "timed out" in msg.lower():
                    last_error = SSHTimeoutError(self.hostname, self.timeout)
                else:
                    last_error = SSHConnectionError(f"SSH 异常: {msg}")
                logger.warning(f"SSH 连接异常 (尝试 {attempt}/{self.max_retry}): {last_error.message}")
                if self._client:
                    self._client.close()
                    self._client = None
                if attempt < self.max_retry:
                    time.sleep(2)
            except socket.timeout:
                last_error = SSHTimeoutError(self.hostname, self.timeout)
                logger.warning(f"SSH 连接超时 (尝试 {attempt}/{self.max_retry}): {last_error.message}")
                if self._client:
                    self._client.close()
                    self._client = None
                if attempt < self.max_retry:
                    time.sleep(2)
            except OSError as e:
                last_error = SSHHostUnreachableError(self.hostname)
                logger.warning(f"SSH 主机不可达 (尝试 {attempt}/{self.max_retry}): {e}")
                if self._client:
                    self._client.close()
                    self._client = None
                if attempt < self.max_retry:
                    time.sleep(2)
            except Exception as e:
                last_error = SSHConnectionError(f"未知连接错误: {e}")
                logger.warning(f"SSH 连接失败 (尝试 {attempt}/{self.max_retry}): {e}")
                if self._client:
                    self._client.close()
                    self._client = None
                if attempt < self.max_retry:
                    time.sleep(2)

        # 所有重试均失败
        logger.error(f"SSH 连接最终失败: {last_error.message if last_error else '未知错误'}")
        return False

    def disconnect(self):
        """断开 SSH 连接"""
        try:
            if self._sftp:
                self._sftp.close()
                self._sftp = None
            if self._client:
                self._client.close()
                self._client = None
        except Exception as e:
            logger.debug(f"断开连接时发生异常: {e}")

    def is_connected(self) -> bool:
        """检查连接是否有效"""
        if self._client is None:
            return False
        try:
            transport = self._client.get_transport()
            if transport is None or not transport.is_active():
                return False
            # 发送 keepalive 检测
            transport.send_ignore()
            return True
        except Exception:
            return False

    def ensure_connected(self) -> bool:
        """确保连接有效，断开时自动重连"""
        if self.is_connected():
            return True
        logger.info("SSH 连接已断开，尝试重连...")
        self.disconnect()
        return self.connect()

    def exec_command(self, command: str, timeout: int = 30,
                     check_error: bool = True) -> tuple:
        """执行远程命令

        Args:
            command: 要执行的命令
            timeout: 超时秒数
            check_error: 是否检查输出中的错误关键词

        Returns:
            (success, stdout, stderr)
        """
        if not self.ensure_connected():
            return False, "", "SSH 连接失败"

        try:
            logger.debug(f"执行命令: {command}")
            stdin, stdout, stderr = self._client.exec_command(
                command, timeout=timeout
            )
            exit_code = stdout.channel.recv_exit_status()
            out = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()

            if out:
                logger.debug(f"stdout: {out[:500]}")
            if err:
                logger.debug(f"stderr: {err[:500]}")

            # 检查错误关键词
            if check_error and ERROR_KEYWORDS:
                combined = out + "\n" + err
                for kw in ERROR_KEYWORDS:
                    if kw.lower() in combined.lower():
                        logger.error(f"检测到错误关键词 [{kw}]: {combined[:300]}")
                        return False, out, f"检测到错误关键词: {kw}"

            if exit_code != 0:
                logger.warning(f"命令退出码={exit_code}: {command}")
                return False, out, err or f"退出码: {exit_code}"

            return True, out, err

        except paramiko.SSHException as e:
            logger.error(f"SSH 执行异常: {e}")
            return False, "", str(e)
        except Exception as e:
            logger.error(f"命令执行异常: {e}")
            return False, "", str(e)

    def exec_command_async(self, command: str, timeout: int = 30,
                           stdout_callback=None, stderr_callback=None,
                           check_error: bool = True) -> int:
        """异步执行远程命令，通过回调获取输出

        Args:
            command: 要执行的命令
            timeout: 超时秒数
            stdout_callback: stdout 行回调函数
            stderr_callback: stderr 行回调函数
            check_error: 是否检查错误关键词

        Returns:
            退出码
        """
        if not self.ensure_connected():
            return -1

        try:
            logger.debug(f"执行命令(异步): {command}")
            stdin, stdout, stderr = self._client.exec_command(
                command, timeout=timeout, get_pty=True
            )
            stdin.close()

            # 读取 stdout
            for line in iter(stdout.readline, ""):
                line = line.rstrip("\n")
                if line:
                    if stdout_callback:
                        stdout_callback(line)
                    if check_error and ERROR_KEYWORDS:
                        for kw in ERROR_KEYWORDS:
                            if kw.lower() in line.lower():
                                logger.error(f"检测到错误关键词 [{kw}]: {line}")
                                if stderr_callback:
                                    stderr_callback(f"[ERROR] 检测到错误关键词: {kw}")
                                return -2

            # 读取 stderr
            for line in iter(stderr.readline, ""):
                line = line.rstrip("\n")
                if line:
                    if stderr_callback:
                        stderr_callback(line)

            exit_code = stdout.channel.recv_exit_status()
            logger.debug(f"命令退出码: {exit_code}")
            return exit_code

        except paramiko.SSHException as e:
            # SSH 连接中断（如板端重启），返回 255
            if "Connection reset" in str(e) or "EOF" in str(e):
                logger.warning(f"SSH 连接中断（可能设备重启）: {e}")
                return 255
            logger.error(f"SSH 异步执行异常: {e}")
            return -1
        except Exception as e:
            logger.error(f"异步命令执行异常: {e}")
            return -1

    def get_sftp(self):
        """获取 SFTP 客户端"""
        if self._sftp is None or self._sftp.sock is None:
            if not self.ensure_connected():
                return None
            try:
                self._sftp = self._client.open_sftp()
            except Exception as e:
                logger.error(f"打开 SFTP 失败: {e}")
                return None
        return self._sftp

    def sftp_put(self, local_path: str, remote_path: str,
                 callback=None) -> bool:
        """通过 SFTP 上传文件

        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            callback: 进度回调函数 (transferred, total)

        Returns:
            是否成功
        """
        try:
            sftp = self.get_sftp()
            if sftp is None:
                return False
            sftp.put(local_path, remote_path, callback=callback)
            logger.info(f"SFTP 上传完成: {local_path} -> {remote_path}")
            return True
        except Exception as e:
            logger.error(f"SFTP 上传失败: {e}")
            return False

    def sftp_get(self, remote_path: str, local_path: str,
                 callback=None) -> bool:
        """通过 SFTP 下载文件"""
        try:
            sftp = self.get_sftp()
            if sftp is None:
                return False
            sftp.get(remote_path, local_path, callback=callback)
            logger.info(f"SFTP 下载完成: {remote_path} -> {local_path}")
            return True
        except Exception as e:
            logger.error(f"SFTP 下载失败: {e}")
            return False

    def check_remote_path_exists(self, remote_path: str) -> bool:
        """检查远程路径是否存在"""
        try:
            sftp = self.get_sftp()
            if sftp is None:
                return False
            sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.warning(f"检查远程路径异常: {e}")
            return False

    def get_remote_disk_space_kb(self, path: str) -> int:
        """获取远程目录可用空间（KB）"""
        success, out, _ = self.exec_command(f"df -Pk {path} | awk 'NR==2{{print $4}}'")
        if success and out:
            try:
                return int(out.strip())
            except ValueError:
                pass
        return 0

    def get_remote_file_size_kb(self, remote_path: str) -> int:
        """获取远程文件大小（KB）"""
        success, out, _ = self.exec_command(f"stat -c%s {remote_path}")
        if success and out:
            try:
                bytes_size = int(out.strip())
                return (bytes_size + 1023) // 1024
            except ValueError:
                pass
        return 0

    def test_connectivity(self) -> bool:
        """测试 SSH 连通性（快速检测）"""
        try:
            success, out, _ = self.exec_command("echo ok", timeout=5)
            return success and "ok" in out
        except Exception:
            return False
