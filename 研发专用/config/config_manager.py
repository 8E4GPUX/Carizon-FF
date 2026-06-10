"""
配置管理模块
负责加密配置文件的读写、IP映射、包类型映射加载
"""
import os
import json
import socket
from cryptography.fernet import Fernet
from utils.logger import get_logger

logger = get_logger()

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CONFIG_DIR)

# 默认配置文件路径
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "deploy_config.enc")
DEFAULT_KEY_PATH = os.path.join(CONFIG_DIR, ".config_key")
MAPPING_PATH = os.path.join(CONFIG_DIR, "package_mapping.json")


def _generate_key() -> bytes:
    """生成 Fernet 加密密钥"""
    return Fernet.generate_key()


def _load_or_create_key(key_path: str = DEFAULT_KEY_PATH) -> bytes:
    """加载或创建加密密钥"""
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            key = f.read()
    else:
        key = _generate_key()
        with open(key_path, "wb") as f:
            f.write(key)
        logger.info(f"已生成新的加密密钥: {key_path}")
    return key


def _encrypt_data(data: dict, key: bytes) -> bytes:
    """加密字典数据"""
    fernet = Fernet(key)
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    return fernet.encrypt(json_str.encode("utf-8"))


def _decrypt_data(encrypted_data: bytes, key: bytes) -> dict:
    """解密数据为字典"""
    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted_data)
    return json.loads(decrypted.decode("utf-8"))


# ========== 默认配置 ==========

DEFAULT_CONFIG = {
    "工控机_IP": "",
    "工控机_用户名": "root",
    "工控机_密码": "Carizon!@#2025",
    "板端_IP": "",
    "板端_用户名": "user",
    "板端_密码": "",
    "板端_密钥文件": "",
    "板端_OTA目录": "/ota",
    "板端_APP目录": "/app",
    "SSH_超时": 8,
    "SSH_重试次数": 3,
    "重启_离线等待": 60,
    "重启_在线等待": 300,
    "额外预留空间_KB": 102400,
    "工控机_临时目录": "/tmp/ota_deploy",
    "清理_命令": "rm -rf {path}/*",
    "赋权_命令": "chmod -R 755 {path}",
    "挂载读写_命令": "mount -o remount rw {path}",
}


def get_local_ip() -> str:
    """获取本机（工控机）IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


def load_ip_mapping() -> list:
    """从 package_mapping.json 加载 IP 映射表"""
    try:
        if os.path.exists(MAPPING_PATH):
            with open(MAPPING_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("ip_mapping", [])
    except Exception as e:
        logger.warning(f"加载 IP 映射表失败: {e}")
    return []


def resolve_target_ip(local_ip: str = None) -> str:
    """根据本机 IP 自动解析目标板端 IP

    Args:
        local_ip: 本机 IP，为 None 时自动获取

    Returns:
        匹配到的板端 IP，未匹配到返回空字符串
    """
    if local_ip is None:
        local_ip = get_local_ip()
    if not local_ip:
        return ""

    mapping = load_ip_mapping()
    for item in mapping:
        if item["local_ip"] == local_ip:
            return item["target_ip"]
    return ""


def load_package_mapping() -> dict:
    """加载包类型映射配置"""
    try:
        if os.path.exists(MAPPING_PATH):
            with open(MAPPING_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"加载包类型映射失败: {e}")
    return {"keyword_mapping": [], "error_keywords": [], "default_cleanup_paths": []}


class ConfigManager:
    """配置管理器（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._config_path = DEFAULT_CONFIG_PATH
        self._key_path = DEFAULT_KEY_PATH
        self._config = dict(DEFAULT_CONFIG)
        self._key = None
        self._load()

    def _load(self):
        """加载配置（若加密文件存在则解密加载）"""
        self._key = _load_or_create_key(self._key_path)

        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "rb") as f:
                    encrypted = f.read()
                self._config = _decrypt_data(encrypted, self._key)
                logger.info("已加载加密配置文件")
            except Exception as e:
                logger.warning(f"解密配置文件失败，使用默认配置: {e}")
                self._config = dict(DEFAULT_CONFIG)
        else:
            logger.info("配置文件不存在，使用默认配置")
            # 尝试自动填充板端 IP
            target_ip = resolve_target_ip()
            if target_ip:
                self._config["板端_IP"] = target_ip
                logger.info(f"自动解析板端 IP: {target_ip}")

    def save(self):
        """保存配置到加密文件"""
        if self._key is None:
            self._key = _load_or_create_key(self._key_path)
        encrypted = _encrypt_data(self._config, self._key)
        with open(self._config_path, "wb") as f:
            f.write(encrypted)
        logger.info("配置文件已保存")

    def get(self, key: str, default=None):
        """获取配置项"""
        return self._config.get(key, default)

    def set(self, key: str, value):
        """设置配置项"""
        self._config[key] = value

    def get_all(self) -> dict:
        """获取全部配置（副本）"""
        return dict(self._config)

    def update(self, data: dict):
        """批量更新配置"""
        self._config.update(data)

    def resolve_and_update_board_ip(self) -> str:
        """重新检测本机 IP，根据映射表自动更新板端 IP

        Returns:
            解析到的板端 IP，未匹配到返回空字符串
        """
        local_ip = get_local_ip()
        if not local_ip:
            logger.warning("无法获取本机 IP，自动解析板端 IP 失败")
            return ""

        target_ip = resolve_target_ip(local_ip)
        if target_ip:
            old_ip = self._config.get("板端_IP", "")
            self._config["板端_IP"] = target_ip
            if old_ip != target_ip:
                logger.info(f"自动解析板端 IP: {local_ip} -> {target_ip} (原: {old_ip or '空'})")
            else:
                logger.info(f"自动解析板端 IP: {local_ip} -> {target_ip} (未变化)")
        else:
            logger.info(f"本机 IP {local_ip} 未匹配到映射表中的板端 IP")
            # 如果板端 IP 为空，尝试用默认规则推断
            if not self._config.get("板端_IP"):
                logger.info("板端 IP 为空，请手动配置或扩展 IP 映射表")

        return target_ip

    def get_ip_mapping_table(self) -> list:
        """获取 IP 映射表（用于界面展示）"""
        return load_ip_mapping()

    @property
    def config_path(self) -> str:
        return self._config_path

    @property
    def key_path(self) -> str:
        return self._key_path
