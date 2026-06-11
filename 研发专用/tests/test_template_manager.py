"""
模板管理器单元测试
"""
import sys
import os
import json
import tempfile
import pytest

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from core.template_manager import DeployTemplate, TemplateManager


class TestDeployTemplate:
    """DeployTemplate 单元测试"""

    def test_create_template(self):
        """测试创建模板"""
        t = DeployTemplate("测试模板", {"工控机_IP": "192.168.1.1"},
                          ["env_model.zip"], ["/data/log"], "测试用模板")
        assert t.name == "测试模板"
        assert t.config["工控机_IP"] == "192.168.1.1"
        assert len(t.packages) == 1
        assert len(t.cleanup_paths) == 1

    def test_to_dict(self):
        """测试转字典"""
        t = DeployTemplate("模板A", {"key": "val"}, ["pkg.zip"])
        d = t.to_dict()
        assert d["name"] == "模板A"
        assert d["config"]["key"] == "val"

    def test_from_dict(self):
        """测试从字典恢复"""
        data = {
            "name": "模板B",
            "config": {"ip": "1.2.3.4"},
            "packages": ["a.zip", "b.zip"],
            "cleanup_paths": [],
            "description": "描述",
            "created_at": "2026-01-01",
            "updated_at": "2026-01-02",
        }
        t = DeployTemplate.from_dict(data)
        assert t.name == "模板B"
        assert t.config["ip"] == "1.2.3.4"
        assert len(t.packages) == 2

    def test_empty_template(self):
        """测试空模板"""
        t = DeployTemplate("空模板")
        assert t.config == {}
        assert t.packages == []
        assert t.cleanup_paths == []


class TestTemplateManager:
    """TemplateManager 单元测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清理"""
        mgr = TemplateManager()
        for t in mgr.list_templates():
            mgr.delete(t.name)
        yield

    def test_save_and_load(self):
        """测试保存和加载"""
        mgr = TemplateManager()
        t = DeployTemplate("测试模板", {"ip": "1.2.3.4"}, ["pkg.zip"])
        assert mgr.save(t) is True
        loaded = mgr.load("测试模板")
        assert loaded is not None
        assert loaded.name == "测试模板"
        assert loaded.config["ip"] == "1.2.3.4"

    def test_delete(self):
        """测试删除"""
        mgr = TemplateManager()
        mgr.save(DeployTemplate("待删除"))
        assert mgr.delete("待删除") is True
        assert mgr.load("待删除") is None

    def test_list_templates(self):
        """测试列出模板"""
        mgr = TemplateManager()
        mgr.save(DeployTemplate("模板1"))
        mgr.save(DeployTemplate("模板2"))
        templates = mgr.list_templates()
        assert len(templates) == 2
        names = [t.name for t in templates]
        assert "模板1" in names
        assert "模板2" in names

    def test_save_overwrite(self):
        """测试覆盖保存"""
        mgr = TemplateManager()
        mgr.save(DeployTemplate("模板", {"v": 1}))
        mgr.save(DeployTemplate("模板", {"v": 2}))
        loaded = mgr.load("模板")
        assert loaded.config["v"] == 2

    def test_export_import(self):
        """测试导出导入"""
        mgr = TemplateManager()
        mgr.save(DeployTemplate("原始模板", {"ip": "1.2.3.4"}, ["pkg.zip"]))

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name
        try:
            assert mgr.export_template("原始模板", export_path) is True
            mgr.delete("原始模板")
            assert mgr.import_template(export_path) is True
            loaded = mgr.load("原始模板")
            assert loaded is not None
            assert loaded.config["ip"] == "1.2.3.4"
        finally:
            os.unlink(export_path)

    def test_load_nonexistent(self):
        """测试加载不存在的模板"""
        mgr = TemplateManager()
        assert mgr.load("不存在的模板") is None

    def test_delete_nonexistent(self):
        """测试删除不存在的模板"""
        mgr = TemplateManager()
        assert mgr.delete("不存在的模板") is False
