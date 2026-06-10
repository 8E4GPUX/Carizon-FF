"""
传输管理器模块
负责 Windows → 工控机 → 板端的双跳文件传输
"""
import os
import time
from core.ssh_client import SSHClient
from utils.logger import get_logger

logger = get_logger()


class TransferManager:
    """传输管理器，处理 Win → 工控机 → 板端的文件传输"""

    def __init__(self, win_to_industrial: SSHClient,
                 industrial_to_board: SSHClient,
                 industrial_temp_dir: str = "/tmp/ota_deploy"):
        """
        Args:
            win_to_industrial: Windows → 工控机的 SSH/SFTP 客户端
            industrial_to_board: 工控机 → 板端的 SSH 客户端
            industrial_temp_dir: 工控机临时目录
        """
        self._win_client = win_to_industrial
        self._board_client = industrial_to_board
        self._temp_dir = industrial_temp_dir
        self._progress_callback = None

    def set_progress_callback(self, callback):
        """设置进度回调函数

        Args:
            callback: (current, total, message) 回调
        """
        self._progress_callback = callback

    def _report_progress(self, current: int, total: int, message: str = ""):
        """报告进度"""
        if self._progress_callback:
            self._progress_callback(current, total, message)

    def _ensure_industrial_temp_dir(self) -> bool:
        """确保工控机临时目录存在"""
        success, _, _ = self._win_client.exec_command(f"mkdir -p {self._temp_dir}")
        return success

    def transfer(self, local_path: str, board_ota_dir: str,
                 filename: str = None) -> bool:
        """执行双跳传输：Windows → 工控机 → 板端

        Args:
            local_path: Windows 本地文件路径
            board_ota_dir: 板端 OTA 目录
            filename: 目标文件名（为 None 则使用原文件名）

        Returns:
            是否成功
        """
        if filename is None:
            filename = os.path.basename(local_path)

        file_size = os.path.getsize(local_path)
        logger.info(f"开始传输: {local_path} ({file_size} bytes)")

        # Step 1: 确保工控机临时目录存在
        self._report_progress(0, 100, "准备工控机临时目录...")
        if not self._ensure_industrial_temp_dir():
            logger.error("创建工控机临时目录失败")
            return False

        # Step 2: Windows → 工控机 (SFTP)
        industrial_path = os.path.join(self._temp_dir, filename).replace("\\", "/")
        self._report_progress(0, 100, f"上传到工控机: {filename}")

        sftp_success = [True]

        def sftp_callback(transferred, total):
            if total > 0:
                pct = min(int(transferred * 100 / total), 99)
                self._report_progress(
                    pct, 100,
                    f"上传到工控机: {filename} ({transferred}/{total} bytes)"
                )

        success = self._win_client.sftp_put(local_path, industrial_path, callback=sftp_callback)
        if not success:
            logger.error("Windows → 工控机 传输失败")
            return False

        self._report_progress(50, 100, f"已上传到工控机，开始传输到板端...")

        # Step 3: 工控机 → 板端 (SCP)
        board_path = f"{board_ota_dir}/{filename}"
        scp_command = (
            f"scp -o ConnectTimeout={self._board_client.timeout} "
            f"-o StrictHostKeyChecking=accept-new "
            f"{industrial_path} "
            f"{self._board_client.username}@{self._board_client.hostname}:{board_path}"
        )

        logger.info(f"工控机 → 板端 SCP: {scp_command}")

        # 使用异步方式执行 SCP，通过回调更新进度
        def stdout_callback(line):
            logger.debug(f"SCP output: {line}")

        exit_code = self._win_client.exec_command_async(
            scp_command, timeout=300,
            stdout_callback=stdout_callback,
            check_error=True
        )

        if exit_code != 0:
            logger.error(f"工控机 → 板端 SCP 失败，退出码: {exit_code}")
            return False

        # Step 4: 验证板端文件存在
        time.sleep(1)
        exists = self._board_client.check_remote_path_exists(board_path)
        if not exists:
            logger.error(f"板端文件不存在（传输可能失败）: {board_path}")
            return False

        # Step 5: 清理工控机临时文件
        self._win_client.exec_command(f"rm -f {industrial_path}")

        self._report_progress(100, 100, f"传输完成: {filename}")
        logger.info(f"传输完成: {local_path} -> {board_path}")
        return True

    def transfer_batch(self, local_paths: list, board_ota_dir: str) -> list:
        """批量传输文件

        Args:
            local_paths: 本地文件路径列表
            board_ota_dir: 板端 OTA 目录

        Returns:
            成功传输的文件名列表
        """
        successful = []
        total = len(local_paths)

        for i, path in enumerate(local_paths):
            filename = os.path.basename(path)
            self._report_progress(
                int(i * 100 / total), 100,
                f"传输文件 ({i + 1}/{total}): {filename}"
            )

            if self.transfer(path, board_ota_dir, filename):
                successful.append(filename)
            else:
                logger.error(f"传输失败: {filename}")
                break

        return successful
