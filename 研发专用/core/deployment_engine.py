"""
部署引擎模块
编排整个部署流程：传输前检查 → 传输 → 板端操作 → 重启监听 → 回滚
"""
import os
import threading
from enum import Enum
from core.ssh_client import SSHClient, set_error_keywords
from core.package_classifier import PackageClassifier, PackageInfo
from core.transfer_manager import TransferManager
from core.board_operator import BoardOperator
from core.rollback_manager import RollbackManager
from config.config_manager import ConfigManager, load_package_mapping
from utils.logger import get_logger

logger = get_logger()


class DeployStatus(Enum):
    """部署状态"""
    IDLE = "idle"
    CHECKING = "checking"
    TRANSFERRING = "transferring"
    BOARD_OPERATING = "board_operating"
    WAITING_REBOOT = "waiting_reboot"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    CANCELLED = "cancelled"


class DeployStep(Enum):
    """部署步骤"""
    INIT = "初始化"
    CHECK_TOOLS = "检查工具"
    CONNECT_INDUSTRIAL = "连接工控机"
    CONNECT_BOARD = "连接板端"
    CHECK_SPACE = "检查空间"
    CLEANUP = "清理板端"
    BACKUP = "备份原目录"
    TRANSFER = "传输文件"
    REMOUNT = "挂载读写"
    UNZIP = "解压包"
    CHMOD = "赋权"
    RUN_OTA_TOOL = "执行 ota_tool"
    RUN_MAP_SCRIPT = "执行 MAP 脚本"
    SYNC = "执行 sync"
    REBOOT = "触发重启"
    WAIT_REBOOT = "等待重启"
    ROLLBACK = "执行回滚"
    DONE = "完成"


class DeploymentEngine:
    """部署引擎，编排整个部署流程"""

    def __init__(self):
        self._config = ConfigManager()
        self._mapping_data = load_package_mapping()
        self._classifier = PackageClassifier(self._mapping_data)

        # 设置错误关键词
        error_kws = self._mapping_data.get("error_keywords", [])
        set_error_keywords(error_kws)

        # SSH 客户端
        self._industrial_client = None
        self._board_client = None

        # 各管理器
        self._transfer_mgr = None
        self._board_op = None
        self._rollback_mgr = RollbackManager()

        # 状态
        self._status = DeployStatus.IDLE
        self._current_step = DeployStep.INIT
        self._current_package = None
        self._cancel_flag = False

        # 回调
        self._status_callback = None
        self._progress_callback = None
        self._log_callback = None
        self._confirm_callback = None

        # 工作线程
        self._worker_thread = None

    # ========== 回调设置 ==========

    def set_status_callback(self, callback):
        """状态变更回调 (status, step, message)"""
        self._status_callback = callback

    def set_progress_callback(self, callback):
        """进度回调 (percent, message)"""
        self._progress_callback = callback

    def set_log_callback(self, callback):
        """日志回调 (level, message)"""
        self._log_callback = callback

    def set_confirm_callback(self, callback):
        """确认回调 (title, message) -> bool"""
        self._confirm_callback = callback

    # ========== 状态更新 ==========

    def _update_status(self, status: DeployStatus, step: DeployStep = None,
                       message: str = ""):
        self._status = status
        if step:
            self._current_step = step
        if self._status_callback:
            self._status_callback(status, step or self._current_step, message)
        if message:
            logger.info(f"[{status.value}] {message}")

    def _update_progress(self, percent: int, message: str = ""):
        if self._progress_callback:
            self._progress_callback(percent, message)

    def _emit_log(self, level: str, message: str):
        if self._log_callback:
            self._log_callback(level, message)

    def _confirm(self, title: str, message: str) -> bool:
        if self._confirm_callback:
            return self._confirm_callback(title, message)
        return False

    # ========== 属性 ==========

    @property
    def status(self) -> DeployStatus:
        return self._status

    @property
    def is_running(self) -> bool:
        return self._status in (DeployStatus.CHECKING, DeployStatus.TRANSFERRING,
                                DeployStatus.BOARD_OPERATING, DeployStatus.WAITING_REBOOT,
                                DeployStatus.ROLLING_BACK)

    @property
    def classifier(self) -> PackageClassifier:
        return self._classifier

    # ========== 取消 ==========

    def cancel(self):
        """取消当前部署"""
        self._cancel_flag = True
        self._update_status(DeployStatus.CANCELLED, message="用户取消部署")

    # ========== 主部署流程 ==========

    def start_deploy(self, file_paths: list, cleanup_paths: list = None,
                     enable_cleanup: bool = False):
        """启动部署（在后台线程中执行）

        Args:
            file_paths: 本地文件路径列表
            cleanup_paths: 清理路径列表
            enable_cleanup: 是否启用清理
        """
        if self.is_running:
            logger.warning("部署正在进行中")
            return

        self._cancel_flag = False
        self._rollback_mgr.clear()

        self._worker_thread = threading.Thread(
            target=self._deploy_worker,
            args=(file_paths, cleanup_paths or [], enable_cleanup),
            daemon=True,
        )
        self._worker_thread.start()

    def _deploy_worker(self, file_paths: list, cleanup_paths: list,
                       enable_cleanup: bool):
        """部署工作线程"""
        try:
            self._execute_deploy(file_paths, cleanup_paths, enable_cleanup)
        except Exception as e:
            logger.error(f"部署异常: {e}", exc_info=True)
            self._update_status(DeployStatus.FAILED, message=f"部署异常: {e}")

    def _execute_deploy(self, file_paths: list, cleanup_paths: list,
                        enable_cleanup: bool):
        """执行部署流程"""
        self._update_status(DeployStatus.CHECKING, DeployStep.INIT, "开始部署流程")

        # Step 1: 分类包
        packages = self._classifier.classify_batch(
            [os.path.basename(p) for p in file_paths]
        )
        unknown = [p for p in packages if not p.is_known]
        if unknown:
            names = [p.filename for p in unknown]
            msg = f"以下包无法识别类型: {', '.join(names)}"
            self._update_status(DeployStatus.FAILED, message=msg)
            return

        # Step 2: 连接工控机
        self._update_status(DeployStatus.CHECKING, DeployStep.CONNECT_INDUSTRIAL,
                            "连接工控机...")
        self._industrial_client = self._create_industrial_client()
        if not self._industrial_client.connect():
            self._update_status(DeployStatus.FAILED, message="连接工控机失败")
            return

        # Step 3: 连接板端（通过工控机跳转）
        self._update_status(DeployStatus.CHECKING, DeployStep.CONNECT_BOARD,
                            "连接板端...")
        self._board_client = self._create_board_client()
        if not self._board_client.connect():
            self._industrial_client.disconnect()
            self._update_status(DeployStatus.FAILED, message="连接板端失败")
            return

        # 设置各管理器
        self._rollback_mgr.set_client(self._board_client)
        self._transfer_mgr = TransferManager(
            self._industrial_client, self._board_client,
            self._config.get("工控机_临时目录", "/tmp/ota_deploy")
        )
        self._transfer_mgr.set_progress_callback(self._progress_callback)

        self._board_op = BoardOperator(
            self._board_client,
            ota_dir=self._config.get("板端_OTA目录", "/ota"),
            app_dir=self._config.get("板端_APP目录", "/app"),
            extra_kb=self._config.get("额外预留空间_KB", 102400),
            offline_wait=self._config.get("重启_离线等待", 60),
            online_wait=self._config.get("重启_在线等待", 300),
        )

        ota_dir = self._config.get("板端_OTA目录", "/ota")
        app_dir = self._config.get("板端_APP目录", "/app")

        # Step 4: 传输前处理（清理 + 空间检查）
        if enable_cleanup and cleanup_paths:
            self._update_status(DeployStatus.CHECKING, DeployStep.CLEANUP,
                                "执行板端清理...")
            self._board_op.execute_cleanup(cleanup_paths)

        # Step 5: 逐个处理包
        total = len(packages)
        for idx, pkg_info in enumerate(packages):
            if self._cancel_flag:
                return

            self._current_package = pkg_info
            local_path = [p for p in file_paths
                          if os.path.basename(p) == pkg_info.filename][0]

            self._update_status(
                DeployStatus.CHECKING,
                message=f"处理包 ({idx + 1}/{total}): {pkg_info.filename}"
            )

            # 5a: 传输文件
            self._update_status(DeployStatus.TRANSFERRING, DeployStep.TRANSFER,
                                f"传输: {pkg_info.filename}")
            if not self._transfer_mgr.transfer(local_path, ota_dir):
                self._handle_failure(pkg_info, "文件传输失败")
                return

            # 5b: 空间检查
            self._update_status(DeployStatus.CHECKING, DeployStep.CHECK_SPACE,
                                "检查板端空间...")
            space_ok, space_msg = self._board_op.check_disk_space(pkg_info.filename)
            if not space_ok:
                # 尝试自动清理
                if self._confirm("空间不足", f"{space_msg}\n是否自动清理 /ota 目录后重试?"):
                    self._board_op.clean_ota_dir()
                    space_ok, space_msg = self._board_op.check_disk_space(pkg_info.filename)
                if not space_ok:
                    self._handle_failure(pkg_info, space_msg)
                    return

            # 5c: 按类型执行板端操作
            self._update_status(DeployStatus.BOARD_OPERATING,
                                message=f"执行板端操作: {pkg_info.filename}")
            success = self._execute_board_ops(pkg_info, app_dir)

            if not success:
                self._handle_failure(pkg_info, f"板端操作失败: {pkg_info.filename}")
                return

            # 5d: 需要重启的包类型，等待重启
            if self._pkg_requires_reboot(pkg_info.pkg_type):
                self._update_status(DeployStatus.WAITING_REBOOT, DeployStep.WAIT_REBOOT,
                                    f"等待设备重启: {pkg_info.filename}")
                if not self._board_op.wait_for_reboot():
                    self._handle_failure(pkg_info, "等待设备重启超时")
                    return

            self._update_progress(
                int((idx + 1) * 100 / total),
                f"包处理完成: {pkg_info.filename}"
            )

        # 全部完成
        self._update_status(DeployStatus.SUCCESS, DeployStep.DONE,
                            "所有包部署完成")
        self._cleanup()

    def _execute_board_ops(self, pkg: PackageInfo, app_dir: str) -> bool:
        """根据包类型执行板端操作

        Args:
            pkg: 包信息
            app_dir: APP 目录

        Returns:
            是否成功
        """
        pkg_type = pkg.pkg_type

        if pkg_type == "app":
            return self._execute_app_ops(pkg, app_dir)
        elif pkg_type == "mcu":
            return self._execute_mcu_ops(pkg)
        elif pkg_type == "full":
            return self._execute_full_ops(pkg)
        elif pkg_type == "map":
            return self._execute_map_ops(pkg)
        else:
            logger.error(f"未知包类型: {pkg_type}")
            return False

    def _execute_app_ops(self, pkg: PackageInfo, app_dir: str) -> bool:
        """执行 APP 类型升级操作"""
        target_dir = pkg.target_dir

        # 1. 挂载读写
        self._update_status(DeployStatus.BOARD_OPERATING, DeployStep.REMOUNT)
        self._board_op.remount_rw(app_dir)
        self._board_op.daemon_reload()

        # 2. 备份原目录
        self._update_status(DeployStatus.BOARD_OPERATING, DeployStep.BACKUP,
                            f"备份原目录: {target_dir}")
        backup_path = self._board_op.backup_target_dir(target_dir)
        self._rollback_mgr.record_backup(backup_path, target_dir, pkg.filename)

        # 3. 解压
        self._update_status(DeployStatus.BOARD_OPERATING, DeployStep.UNZIP,
                            f"解压: {pkg.filename}")
        if not self._board_op.unzip_package(pkg.filename, app_dir):
            return False

        # 4. 删除上传包
        self._board_op.remove_ota_package(pkg.filename)

        # 5. 赋权
        self._update_status(DeployStatus.BOARD_OPERATING, DeployStep.CHMOD,
                            f"赋权: {target_dir}")
        self._board_op.chmod_dir(target_dir)

        # 6. sync + reboot
        self._update_status(DeployStatus.BOARD_OPERATING, DeployStep.SYNC)
        self._board_op.sync()

        self._update_status(DeployStatus.BOARD_OPERATING, DeployStep.REBOOT,
                            "触发重启")
        self._board_op.reboot()

        return True

    def _execute_mcu_ops(self, pkg: PackageInfo) -> bool:
        """执行 MCU 类型升级操作"""
        self._update_status(DeployStatus.BOARD_OPERATING, DeployStep.RUN_OTA_TOOL,
                            f"MCU 升级: {pkg.filename}")
        success, exit_code, output = self._board_op.run_ota_tool(
            pkg.filename, mcu_mode=True
        )
        return success

    def _execute_full_ops(self, pkg: PackageInfo) -> bool:
        """执行整包升级操作"""
        self._update_status(DeployStatus.BOARD_OPERATING, DeployStep.RUN_OTA_TOOL,
                            f"整包升级: {pkg.filename}")
        success, exit_code, output = self._board_op.run_ota_tool(
            pkg.filename, mcu_mode=False
        )
        return success

    def _execute_map_ops(self, pkg: PackageInfo) -> bool:
        """执行 MAP 类型升级操作"""
        self._update_status(DeployStatus.BOARD_OPERATING, DeployStep.RUN_MAP_SCRIPT,
                            f"MAP 升级: {pkg.filename}")
        if not self._board_op.run_map_update(pkg.filename):
            return False

        self._update_status(DeployStatus.BOARD_OPERATING, DeployStep.SYNC)
        self._board_op.sync()

        self._update_status(DeployStatus.BOARD_OPERATING, DeployStep.REBOOT,
                            "触发重启")
        self._board_op.reboot()

        return True

    def _pkg_requires_reboot(self, pkg_type: str) -> bool:
        """判断包类型是否需要等待重启"""
        return pkg_type in ("app", "map", "full")

    def _handle_failure(self, pkg: PackageInfo, message: str):
        """处理失败：回滚 + 更新状态"""
        logger.error(f"部署失败: {message}")

        self._update_status(DeployStatus.ROLLING_BACK, DeployStep.ROLLBACK,
                            f"部署失败，执行回滚: {message}")

        if self._rollback_mgr.has_records:
            self._rollback_mgr.rollback_all()

        self._update_status(DeployStatus.FAILED, message=message)
        self._cleanup()

    def _cleanup(self):
        """清理资源"""
        if self._industrial_client:
            self._industrial_client.disconnect()
        if self._board_client:
            self._board_client.disconnect()

    # ========== SSH 客户端创建 ==========

    def _create_industrial_client(self) -> SSHClient:
        """创建工控机 SSH 客户端"""
        return SSHClient(
            hostname=self._config.get("工控机_IP", ""),
            username=self._config.get("工控机_用户名", ""),
            password=self._config.get("工控机_密码", ""),
            timeout=self._config.get("SSH_超时", 8),
            retry=self._config.get("SSH_重试次数", 3),
        )

    def _create_board_client(self) -> SSHClient:
        """创建板端 SSH 客户端（从配置读取用户名/密码/密钥）"""
        return SSHClient(
            hostname=self._config.get("板端_IP", ""),
            username=self._config.get("板端_用户名", "user"),
            password=self._config.get("板端_密码", ""),
            key_file=self._config.get("板端_密钥文件", ""),
            timeout=self._config.get("SSH_超时", 8),
            retry=self._config.get("SSH_重试次数", 3),
        )
