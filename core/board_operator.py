"""
板端操作模块
封装板端各类操作：空间检查、备份、解压、赋权、清理、重启监听等
"""
import time
from core.ssh_client import SSHClient
from utils.logger import get_logger

logger = get_logger()


class BoardOperator:
    """板端操作器"""

    def __init__(self, board_client: SSHClient,
                 ota_dir: str = "/ota",
                 app_dir: str = "/app",
                 extra_kb: int = 102400,
                 offline_wait: int = 60,
                 online_wait: int = 300):
        """
        Args:
            board_client: 板端 SSH 客户端
            ota_dir: 板端 OTA 目录
            app_dir: 板端 APP 目录
            extra_kb: 额外预留空间 KB
            offline_wait: 等待设备离线超时（秒）
            online_wait: 等待设备上线超时（秒）
        """
        self._client = board_client
        self._ota_dir = ota_dir
        self._app_dir = app_dir
        self._extra_kb = extra_kb
        self._offline_wait = offline_wait
        self._online_wait = online_wait

    def check_disk_space(self, package_name: str) -> tuple:
        """检查板端 /ota 磁盘空间是否充足

        Args:
            package_name: 包名（用于获取包大小）

        Returns:
            (success, message)
        """
        remote_path = f"{self._ota_dir}/{package_name}"
        pkg_size_kb = self._client.get_remote_file_size_kb(remote_path)
        avail_kb = self._client.get_remote_disk_space_kb(self._ota_dir)
        total_need = pkg_size_kb + self._extra_kb

        logger.info(
            f"空间检查: 包={package_name}, "
            f"大小={pkg_size_kb}KB, "
            f"/ota 可用={avail_kb}KB, "
            f"需要>={total_need}KB"
        )

        if avail_kb < total_need:
            msg = (f"/ota 空间不足: 可用 {avail_kb}KB, "
                   f"需要 {total_need}KB (包 {pkg_size_kb}KB + 预留 {self._extra_kb}KB)")
            logger.warning(msg)
            return False, msg

        return True, f"空间充足 (可用 {avail_kb}KB, 需要 {total_need}KB)"

    def clean_ota_dir(self) -> bool:
        """清理板端 /ota 目录"""
        logger.info(f"清理板端 {self._ota_dir} 目录")
        success, out, err = self._client.exec_command(
            f"cd {self._ota_dir} && rm -rf -- * .[!.]* ..?* 2>/dev/null || true"
        )
        if success:
            logger.info(f"/ota 目录清理完成")
        else:
            logger.warning(f"/ota 目录清理可能未完全成功: {err}")
        return True  # 清理失败不阻断流程

    def remount_rw(self, mount_path: str = None) -> bool:
        """重新挂载为读写

        Args:
            mount_path: 挂载路径，默认 /app
        """
        path = mount_path or self._app_dir
        logger.info(f"重新挂载为读写: {path}")
        success, out, err = self._client.exec_command(
            f"mount -o remount rw {path}"
        )
        if not success:
            logger.warning(f"重新挂载失败: {err}")
        return success

    def daemon_reload(self) -> bool:
        """执行 systemctl daemon-reload"""
        logger.info("执行 systemctl daemon-reload")
        success, out, err = self._client.exec_command("systemctl daemon-reload")
        return success

    def backup_target_dir(self, target_dir: str) -> str:
        """备份板端目标目录

        Args:
            target_dir: 目标目录名（如 env_model）

        Returns:
            备份路径，失败返回空字符串
        """
        source = f"{self._app_dir}/{target_dir}"
        timestamp = time.strftime("%Y%m%d%H%M%S")
        backup_name = f"{target_dir}_old_{timestamp}"
        backup_path = f"{self._ota_dir}/{backup_name}"

        # 检查源目录是否存在
        exists = self._client.check_remote_path_exists(source)
        if not exists:
            logger.warning(f"目标目录不存在，跳过备份: {source}")
            return ""

        logger.info(f"备份: {source} -> {backup_path}")
        success, out, err = self._client.exec_command(
            f"mv {source} {backup_path}"
        )
        if success:
            logger.info(f"备份完成: {backup_path}")
            return backup_path
        else:
            logger.error(f"备份失败: {err}")
            return ""

    def unzip_package(self, package_name: str, target_base: str = None) -> bool:
        """解压包到目标目录

        Args:
            package_name: 包名
            target_base: 解压目标基目录，默认 /app

        Returns:
            是否成功
        """
        target = target_base or self._app_dir
        pkg_path = f"{self._ota_dir}/{package_name}"
        logger.info(f"解压: {pkg_path} -> {target}")

        success, out, err = self._client.exec_command(
            f"cd {self._ota_dir} && unzip -o {pkg_path} -d {target}"
        )
        if success:
            logger.info("解压完成")
        else:
            logger.error(f"解压失败: {err}")
        return success

    def remove_ota_package(self, package_name: str) -> bool:
        """删除板端 /ota 下的包文件"""
        pkg_path = f"{self._ota_dir}/{package_name}"
        success, out, err = self._client.exec_command(f"rm -f {pkg_path}")
        return success

    def sync(self) -> bool:
        """执行 sync 命令"""
        logger.info("执行 sync")
        success, out, err = self._client.exec_command("sync")
        return success

    def chmod_dir(self, target_dir: str, mode: str = "755") -> bool:
        """对目标目录执行赋权

        Args:
            target_dir: 目标目录（相对于 /app 或绝对路径）
            mode: 权限模式，默认 755
        """
        path = target_dir if target_dir.startswith("/") else f"{self._app_dir}/{target_dir}"
        logger.info(f"赋权: chmod -R {mode} {path}")
        success, out, err = self._client.exec_command(f"chmod -R {mode} {path}")
        if success:
            logger.info(f"赋权完成: {path}")
        else:
            logger.error(f"赋权失败: {err}")
        return success

    def reboot(self) -> bool:
        """触发板端重启（后台方式）"""
        logger.info("触发板端重启")
        # 使用 nohup 后台重启，避免 SSH 被立即中断
        success, out, err = self._client.exec_command(
            "nohup sh -c 'sleep 1; reboot' >/dev/null 2>&1 &"
        )
        logger.info("重启命令已发送")
        return True

    def wait_for_offline(self) -> bool:
        """等待设备离线

        Returns:
            是否在超时内检测到离线
        """
        logger.info(f"等待设备离线 (超时 {self._offline_wait}s)...")
        for i in range(1, self._offline_wait + 1):
            if not self._client.test_connectivity():
                logger.info(f"设备已离线 (耗时 {i}s)")
                return True
            if i % 10 == 0:
                logger.info(f"等待离线中... ({i}s)")
            time.sleep(1)
        logger.warning(f"等待设备离线超时 ({self._offline_wait}s)")
        return False

    def wait_for_online(self) -> bool:
        """等待设备上线

        Returns:
            是否在超时内检测到上线
        """
        logger.info(f"等待设备上线 (超时 {self._online_wait}s)...")
        for i in range(1, self._online_wait + 1):
            if self._client.test_connectivity():
                logger.info(f"设备已上线 (耗时 {i}s)")
                return True
            if i % 30 == 0:
                logger.info(f"等待上线中... ({i}s)")
            time.sleep(1)
        logger.warning(f"等待设备上线超时 ({self._online_wait}s)")
        return False

    def wait_for_reboot(self) -> bool:
        """等待设备重启完成（离线 + 上线）

        Returns:
            是否成功
        """
        if not self.wait_for_offline():
            # 可能重启太快没检测到离线，直接尝试等待上线
            logger.info("未检测到离线，直接尝试等待上线...")
        return self.wait_for_online()

    def run_ota_tool(self, package_name: str, mcu_mode: bool = False) -> tuple:
        """执行 ota_tool 升级

        Args:
            package_name: 包名
            mcu_mode: 是否为 MCU 模式

        Returns:
            (success, exit_code, output)
        """
        pkg_path = f"{self._ota_dir}/{package_name}"
        if mcu_mode:
            cmd = f"cd {self._ota_dir} && ota_tool -p {pkg_path}:mcu"
        else:
            cmd = f"cd {self._ota_dir} && ota_tool -p {pkg_path}"

        logger.info(f"执行 ota_tool: {cmd}")

        # 使用异步方式获取实时输出
        output_lines = []

        def cb(line):
            output_lines.append(line)
            logger.info(f"[ota_tool] {line}")

        exit_code = self._client.exec_command_async(
            cmd, timeout=600,
            stdout_callback=cb, stderr_callback=cb
        )

        output = "\n".join(output_lines)

        if exit_code == 255:
            # 整包升级时 SSH 断开视为正常
            logger.warning("ota_tool 执行期间 SSH 连接中断 (exit=255)，视为正常")
            return True, exit_code, output
        elif exit_code == 0:
            logger.info("ota_tool 执行成功")
            return True, exit_code, output
        else:
            logger.error(f"ota_tool 执行失败，退出码: {exit_code}")
            return False, exit_code, output

    def run_map_update(self, package_name: str) -> bool:
        """执行 MAP 升级脚本

        Args:
            package_name: 包名

        Returns:
            是否成功
        """
        logger.info(f"执行 MAP 升级: {package_name}")

        # 解压
        success, out, err = self._client.exec_command(
            f"cd {self._ota_dir} && unzip -o {package_name}"
        )
        if not success:
            logger.error(f"MAP 包解压失败: {err}")
            return False

        # 查找并执行 map_update 脚本
        script_find_cmd = (
            f'cd {self._ota_dir} && '
            f'script_path=""; '
            f'[ -f map_update.sh9 ] && script_path=map_update.sh9; '
            f'[ -f map_update.sh ] && script_path=map_update.sh; '
            f'[ -z "$script_path" ] && script_path=$(find . -maxdepth 3 '
            f'\\( -name map_update.sh9 -o -name map_update.sh \\) | head -n 1); '
            f'if [ -z "$script_path" ]; then echo "NO_SCRIPT_FOUND"; '
            f'else chmod +x "$script_path" && bash "$script_path"; fi'
        )

        success, out, err = self._client.exec_command(
            script_find_cmd, timeout=600
        )

        if "NO_SCRIPT_FOUND" in out:
            logger.error("未找到 map_update.sh9/map_update.sh")
            return False

        if not success:
            logger.error(f"MAP 升级脚本执行失败: {err}")
            return False

        logger.info("MAP 升级脚本执行完成")
        return True

    def execute_cleanup(self, paths: list) -> bool:
        """执行板端数据清理

        Args:
            paths: 待清理的路径列表

        Returns:
            是否成功
        """
        all_success = True
        for path in paths:
            logger.info(f"清理: {path}")
            success, out, err = self._client.exec_command(
                f"rm -rf {path}/* {path}/.* 2>/dev/null || true"
            )
            if not success:
                logger.warning(f"清理 {path} 可能未完全成功: {err}")
                all_success = False
        return all_success
