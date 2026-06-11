"""
配置管理器单元测试
"""
import sys
import os
import json
import tempfile
import pytest

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from config.config_manager import ConfigManager, load_package_mapping, get_local_ip, resolve_target_ip


class TestConfigManager:
    """ConfigManager 单元测试"""

    def test_singleton(self):
        """测试单例模式"""
        cm1 = ConfigManager()
        cm2 = ConfigManager()
        assert cm1 is cm2

    def test_default_config_values(self):
        """测试默认配置值"""
        cm = ConfigManager()
        assert cm.get("SSH_超时") == 8
        assert cm.get("SSH_重试次数") == 3
        assert cm.get("板端_用户名") == "user"
        # 板端_密码 和 板端_密钥文件 可能为 None（旧配置）或 ""（新配置）
        pwd = cm.get("板端_密码")
        assert pwd is None or pwd == ""
        key = cm.get("板端_密钥文件")
        assert key is None or key == ""

    def test_get_with_default(self):
        """测试 get 方法默认值"""
        cm = ConfigManager()
        assert cm.get("不存在的配置", "默认值") == "默认值"
        assert cm.get("不存在的配置") is None

    def test_set_and_get(self):
        """测试 set 和 get"""
        cm = ConfigManager()
        cm.set("测试项", "测试值")
        assert cm.get("测试项") == "测试值"

    def test_update(self):
        """测试批量更新"""
        cm = ConfigManager()
        cm.update({"项1": "值1", "项2": "值2"})
        assert cm.get("项1") == "值1"
        assert cm.get("项2") == "值2"

    def test_get_all(self):
        """测试获取全部配置"""
        cm = ConfigManager()
        all_config = cm.get_all()
        assert isinstance(all_config, dict)
        assert "工控机_IP" in all_config
        assert "板端_IP" in all_config

    def test_get_all_is_copy(self):
        """测试 get_all 返回的是副本"""
        cm = ConfigManager()
        all_config = cm.get_all()
        all_config["测试修改"] = "修改"
        assert cm.get("测试修改") is None

    def test_config_path_property(self):
        """测试 config_path 属性"""
        cm = ConfigManager()
        assert cm.config_path.endswith("deploy_config.enc")

    def test_key_path_property(self):
        """测试 key_path 属性"""
        cm = ConfigManager()
        assert cm.key_path.endswith(".config_key")


class TestLoadPackageMapping:
    """load_package_mapping 单元测试"""

    def test_load_mapping_has_required_keys(self):
        """测试加载的映射包含必要键"""
        mapping = load_package_mapping()
        assert "keyword_mapping" in mapping
        assert "error_keywords" in mapping
        assert "default_cleanup_paths" in mapping

    def test_keyword_mapping_is_list(self):
        """测试 keyword_mapping 是列表"""
        mapping = load_package_mapping()
        assert isinstance(mapping["keyword_mapping"], list)

    def test_keyword_mapping_has_entries(self):
        """测试 keyword_mapping 有内容"""
        mapping = load_package_mapping()
        assert len(mapping["keyword_mapping"]) > 0

    def test_each_mapping_has_required_fields(self):
        """测试每个映射项有必填字段"""
        mapping = load_package_mapping()
        for item in mapping["keyword_mapping"]:
            assert "keyword" in item
            assert "type" in item

    def test_error_keywords_is_list(self):
        """测试 error_keywords 是列表"""
        mapping = load_package_mapping()
        assert isinstance(mapping["error_keywords"], list)

    def test_cleanup_paths_is_list(self):
        """测试 default_cleanup_paths 是列表"""
        mapping = load_package_mapping()
        assert isinstance(mapping["default_cleanup_paths"], list)


class TestGetLocalIp:
    """get_local_ip 单元测试"""

    def test_get_local_ip_returns_string(self):
        """测试获取本机 IP 返回字符串"""
        ip = get_local_ip()
        assert isinstance(ip, str)

    def test_get_local_ip_format(self):
        """测试 IP 格式"""
        ip = get_local_ip()
        if ip:
            parts = ip.split(".")
            assert len(parts) == 4
            for part in parts:
                assert part.isdigit()
                assert 0 <= int(part) <= 255


class TestResolveTargetIp:
    """resolve_target_ip 单元测试"""

    def test_resolve_with_known_ip(self):
        """测试已知 IP 解析"""
        target = resolve_target_ip("172.31.48.102")
        assert target == "172.31.48.9"

    def test_resolve_with_another_known_ip(self):
        """测试另一个已知 IP 解析"""
        target = resolve_target_ip("192.168.2.102")
        assert target == "192.168.2.62"

    def test_resolve_with_unknown_ip(self):
        """测试未知 IP 解析"""
        target = resolve_target_ip("10.0.0.1")
        assert target == ""

    def test_resolve_with_empty_ip(self):
        """测试空 IP 解析"""
        target = resolve_target_ip("")
        assert target == ""

    def test_resolve_with_none(self):
        """测试 None IP 解析"""
        target = resolve_target_ip(None)
        assert target == ""


class TestValidateConfig:
    """配置验证单元测试"""

    def test_validate_valid_config(self):
        """测试有效配置"""
        cm = ConfigManager()
        cm.set("工控机_IP", "192.168.1.100")
        cm.set("板端_IP", "172.31.48.9")
        is_valid, errors = cm.validate_config()
        assert is_valid is True
        assert errors == []

    def test_validate_invalid_industrial_ip(self):
        """测试无效工控机 IP"""
        cm = ConfigManager()
        cm.set("工控机_IP", "999.999.999.999")
        is_valid, errors = cm.validate_config()
        assert is_valid is False
        assert "工控机 IP 格式错误" in errors

    def test_validate_invalid_board_ip(self):
        """测试无效板端 IP"""
        cm = ConfigManager()
        cm.set("板端_IP", "abc.def.ghi.jkl")
        is_valid, errors = cm.validate_config()
        assert is_valid is False
        assert "板端 IP 格式错误" in errors

    def test_validate_ip_out_of_range(self):
        """测试 IP 超出范围"""
        cm = ConfigManager()
        cm.set("工控机_IP", "192.168.1.300")
        is_valid, errors = cm.validate_config()
        assert is_valid is False
        assert "工控机 IP 格式错误" in errors

    def test_validate_ota_dir_not_start_with_slash(self):
        """测试 OTA 目录不以 / 开头"""
        cm = ConfigManager()
        cm.set("板端_OTA目录", "ota")
        is_valid, errors = cm.validate_config()
        assert is_valid is False
        assert "板端 OTA 目录必须以 / 开头" in errors

    def test_validate_app_dir_not_start_with_slash(self):
        """测试 APP 目录不以 / 开头"""
        cm = ConfigManager()
        cm.set("板端_APP目录", "app")
        is_valid, errors = cm.validate_config()
        assert is_valid is False
        assert "板端 APP 目录必须以 / 开头" in errors

    def test_validate_temp_dir_not_start_with_slash(self):
        """测试临时目录不以 / 开头"""
        cm = ConfigManager()
        cm.set("工控机_临时目录", "tmp/ota")
        is_valid, errors = cm.validate_config()
        assert is_valid is False
        assert "工控机临时目录必须以 / 开头" in errors

    def test_validate_ssh_timeout_too_low(self):
        """测试 SSH 超时过低"""
        cm = ConfigManager()
        cm.set("SSH_超时", 0)
        is_valid, errors = cm.validate_config()
        assert is_valid is False
        assert "SSH 超时时间必须在 1~120 秒之间" in errors

    def test_validate_ssh_timeout_too_high(self):
        """测试 SSH 超时过高"""
        cm = ConfigManager()
        cm.set("SSH_超时", 200)
        is_valid, errors = cm.validate_config()
        assert is_valid is False
        assert "SSH 超时时间必须在 1~120 秒之间" in errors

    def test_validate_ssh_retry_negative(self):
        """测试 SSH 重试次数为负数"""
        cm = ConfigManager()
        cm.set("SSH_重试次数", -1)
        is_valid, errors = cm.validate_config()
        assert is_valid is False
        assert "SSH 重试次数必须在 0~20 之间" in errors

    def test_validate_empty_ip_skipped(self):
        """测试空 IP 跳过验证"""
        cm = ConfigManager()
        # 重置所有可能受前序测试影响的配置项
        cm.set("工控机_IP", "")
        cm.set("板端_IP", "")
        cm.set("板端_OTA目录", "/ota")
        cm.set("板端_APP目录", "/app")
        cm.set("工控机_临时目录", "/tmp/ota_deploy")
        cm.set("SSH_超时", 8)
        cm.set("SSH_重试次数", 3)
        is_valid, errors = cm.validate_config()
        assert is_valid is True, f"验证失败: {errors}"

    def test_validate_multiple_errors(self):
        """测试多个错误同时返回"""
        cm = ConfigManager()
        cm.set("工控机_IP", "invalid")
        cm.set("板端_IP", "bad")
        cm.set("板端_OTA目录", "ota")
        cm.set("SSH_超时", 0)
        is_valid, errors = cm.validate_config()
        assert is_valid is False
        assert len(errors) >= 3


class TestValidateIp:
    """_validate_ip 静态方法测试"""

    def test_valid_ip(self):
        """测试有效 IP"""
        assert ConfigManager._validate_ip("192.168.1.1") is True

    def test_valid_ip_zeros(self):
        """测试全零 IP"""
        assert ConfigManager._validate_ip("0.0.0.0") is True

    def test_valid_ip_max(self):
        """测试最大 IP"""
        assert ConfigManager._validate_ip("255.255.255.255") is True

    def test_invalid_ip_too_many_parts(self):
        """测试 IP 段过多"""
        assert ConfigManager._validate_ip("1.2.3.4.5") is False

    def test_invalid_ip_too_few_parts(self):
        """测试 IP 段过少"""
        assert ConfigManager._validate_ip("1.2.3") is False

    def test_invalid_ip_non_numeric(self):
        """测试非数字 IP"""
        assert ConfigManager._validate_ip("abc.def.ghi.jkl") is False

    def test_invalid_ip_out_of_range(self):
        """测试 IP 超出范围"""
        assert ConfigManager._validate_ip("256.1.2.3") is False

    def test_invalid_ip_empty(self):
        """测试空 IP"""
        assert ConfigManager._validate_ip("") is False

    def test_invalid_ip_with_spaces(self):
        """测试带空格的 IP"""
        assert ConfigManager._validate_ip("192.168.1.1 ") is False
