"""
回滚管理模块
负责在升级失败时自动恢复备份目录
"""
from utils.logger import get_logger

logger = get_logger()


class RollbackManager:
    """回滚管理器，记录备份信息并在失败时执行回滚"""

    def __init__(self, board_client=None, ota_dir: str = "/ota",
                 app_dir: str = "/app"):
        """
        Args:
            board_client: 板端 SSH 客户端
            ota_dir: 板端 OTA 目录
            app_dir: 板端 APP 目录
        """
        self._client = board_client
        self._ota_dir = ota_dir
        self._app_dir = app_dir
        # 备份记录列表: [(backup_path, original_target_dir, package_name), ...]
        self._backup_records = []

    def set_client(self, board_client):
        """设置板端 SSH 客户端"""
        self._client = board_client

    def record_backup(self, backup_path: str, target_dir: str,
                      package_name: str):
        """记录一次备份

        Args:
            backup_path: 备份路径（如 /ota/env_model_old_20260608120000）
            target_dir: 原目标目录名（如 env_model）
            package_name: 对应的包名
        """
        if backup_path:
            self._backup_records.append({
                "backup_path": backup_path,
                "target_dir": target_dir,
                "package_name": package_name,
            })
            logger.info(f"记录备份: {backup_path} -> {target_dir}")

    def rollback_last(self) -> bool:
        """回滚最后一次备份

        Returns:
            是否成功
        """
        if not self._backup_records:
            logger.warning("无备份记录，无法回滚")
            return False

        record = self._backup_records[-1]
        return self._rollback_single(record)

    def rollback_all(self) -> bool:
        """回滚所有备份（逆序）

        Returns:
            是否全部成功
        """
        if not self._backup_records:
            logger.warning("无备份记录，无法回滚")
            return False

        all_success = True
        for record in reversed(self._backup_records):
            if not self._rollback_single(record):
                all_success = False
        return all_success

    def rollback_by_package(self, package_name: str) -> bool:
        """回滚指定包对应的备份

        Args:
            package_name: 包名

        Returns:
            是否成功
        """
        for record in self._backup_records:
            if record["package_name"] == package_name:
                return self._rollback_single(record)
        logger.warning(f"未找到包 {package_name} 的备份记录")
        return False

    def _rollback_single(self, record: dict) -> bool:
        """执行单次回滚

        Args:
            record: 备份记录

        Returns:
            是否成功
        """
        backup_path = record["backup_path"]
        target_dir = record["target_dir"]
        target_path = f"{self._app_dir}/{target_dir}"

        logger.info(f"执行回滚: {backup_path} -> {target_path}")

        if self._client is None:
            logger.error("SSH 客户端未设置，无法执行回滚")
            return False

        # 检查备份是否存在
        exists = self._client.check_remote_path_exists(backup_path)
        if not exists:
            logger.warning(f"备份路径不存在，跳过回滚: {backup_path}")
            return False

        # 先删除当前目录（如果存在）
        self._client.exec_command(f"rm -rf {target_path}")

        # 将备份移回
        success, out, err = self._client.exec_command(
            f"mv {backup_path} {target_path}"
        )

        if success:
            logger.info(f"回滚成功: {backup_path} -> {target_path}")
            return True
        else:
            logger.error(f"回滚失败: {err}")
            return False

    @property
    def has_records(self) -> bool:
        """是否有备份记录"""
        return len(self._backup_records) > 0

    @property
    def record_count(self) -> int:
        return len(self._backup_records)

    def clear(self):
        """清空备份记录"""
        self._backup_records.clear()
        logger.debug("备份记录已清空")
