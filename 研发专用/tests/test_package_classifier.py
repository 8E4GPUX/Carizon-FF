"""
包分类器单元测试
"""
import sys
import os
import json
import tempfile
import pytest

# 确保项目根目录在 sys.path 中
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from core.package_classifier import PackageClassifier, PackageInfo


class TestPackageClassifier:
    """PackageClassifier 单元测试"""

    @pytest.fixture
    def classifier(self):
        """创建测试用的分类器实例"""
        mapping_data = {
            "keyword_mapping": [
                {"keyword": "mcu", "type": "mcu", "target_dir": ""},
                {"keyword": "env_model", "type": "app", "target_dir": "env_model"},
                {"keyword": "odometry", "type": "app", "target_dir": "odometry"},
                {"keyword": "pvs", "type": "full", "target_dir": ""},
                {"keyword": "vff", "type": "full", "target_dir": ""},
                {"keyword": "drivememomap", "type": "map", "target_dir": ""},
                {"keyword": "perception", "type": "app", "target_dir": "adas"},
                {"keyword": "calibration", "type": "app", "target_dir": "calib_app"},
            ],
            "error_keywords": ["空间不足", "权限拒绝", "not found"],
            "default_cleanup_paths": ["/data/log", "/data/cache"],
        }
        return PackageClassifier(mapping_data)

    def test_classify_app_package(self, classifier):
        """测试 APP 类型包识别"""
        result = classifier.classify("env_model_v1.0.zip")
        assert result.pkg_type == "app"
        assert result.target_dir == "env_model"
        assert result.is_known is True

    def test_classify_mcu_package(self, classifier):
        """测试 MCU 类型包识别"""
        result = classifier.classify("mcu_firmware_v2.1.zip")
        assert result.pkg_type == "mcu"
        assert result.is_known is True

    def test_classify_full_package(self, classifier):
        """测试整包类型识别"""
        result = classifier.classify("pvs_system_v3.0.zip")
        assert result.pkg_type == "full"
        assert result.is_known is True

    def test_classify_map_package(self, classifier):
        """测试地图包类型识别"""
        result = classifier.classify("drivememomap_v1.5.zip")
        assert result.pkg_type == "map"
        assert result.is_known is True

    def test_classify_unknown_package(self, classifier):
        """测试未知包类型识别"""
        result = classifier.classify("unknown_file.tar.gz")
        assert result.pkg_type == "unknown"
        assert result.is_known is False

    def test_classify_special_mapping(self, classifier):
        """测试特殊映射（perception→adas）"""
        result = classifier.classify("perception_module.zip")
        assert result.pkg_type == "app"
        assert result.target_dir == "adas"

    def test_classify_calibration_mapping(self, classifier):
        """测试特殊映射（calibration→calib_app）"""
        result = classifier.classify("calibration_data.zip")
        assert result.pkg_type == "app"
        assert result.target_dir == "calib_app"

    def test_classify_case_insensitive(self, classifier):
        """测试大小写不敏感"""
        result = classifier.classify("MCU_FIRMWARE.zip")
        assert result.pkg_type == "mcu"

    def test_classify_batch(self, classifier):
        """测试批量分类"""
        filenames = [
            "env_model_v1.0.zip",
            "mcu_firmware.zip",
            "unknown.tar.gz",
            "pvs_system.zip",
        ]
        results = classifier.classify_batch(filenames)
        assert len(results) == 4
        assert results[0].pkg_type == "app"
        assert results[1].pkg_type == "mcu"
        assert results[2].pkg_type == "unknown"
        assert results[3].pkg_type == "full"

    def test_classify_empty_filename(self, classifier):
        """测试空文件名"""
        result = classifier.classify("")
        assert result.pkg_type == "unknown"
        assert result.is_known is False

    def test_classify_no_extension(self, classifier):
        """测试无扩展名文件"""
        result = classifier.classify("env_model")
        assert result.pkg_type == "app"
        assert result.target_dir == "env_model"

    def test_error_keywords_property(self, classifier):
        """测试 error_keywords 属性"""
        assert "空间不足" in classifier.error_keywords
        assert "not found" in classifier.error_keywords

    def test_cleanup_paths_property(self, classifier):
        """测试 cleanup_paths 属性"""
        assert "/data/log" in classifier.cleanup_paths
        assert "/data/cache" in classifier.cleanup_paths

    def test_package_info_repr(self):
        """测试 PackageInfo __repr__"""
        info = PackageInfo("test.zip", "app", "test_dir")
        repr_str = repr(info)
        assert "test.zip" in repr_str
        assert "app" in repr_str
        assert "test_dir" in repr_str

    def test_package_info_unknown_defaults(self):
        """测试 PackageInfo 默认值"""
        info = PackageInfo("test.zip")
        assert info.pkg_type == "unknown"
        assert info.target_dir == "unknown"
        assert info.is_known is False


class TestPackageClassifierWithRealConfig:
    """使用真实配置文件的集成测试"""

    def test_load_from_real_config(self):
        """测试从真实配置文件加载"""
        from config.config_manager import load_package_mapping
        mapping = load_package_mapping()
        assert "keyword_mapping" in mapping
        assert len(mapping["keyword_mapping"]) > 0

        classifier = PackageClassifier(mapping)
        # 测试真实配置中的包类型
        for rule in mapping["keyword_mapping"]:
            keyword = rule["keyword"]
            result = classifier.classify(f"{keyword}_test.zip")
            assert result.pkg_type == rule["type"]
            assert result.target_dir == rule.get("target_dir", "")
