"""
部署历史单元测试
"""
import sys
import os
import json
import tempfile
import pytest

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from core.deploy_history import DeployHistory


class TestDeployHistory:
    """DeployHistory 单元测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前重置单例"""
        history = DeployHistory()
        # 清空测试数据
        history._conn.execute("DELETE FROM deploy_records")
        history._conn.execute("DELETE FROM deploy_packages")
        history._conn.commit()
        yield

    def test_start_record(self):
        """测试开始记录"""
        history = DeployHistory()
        record_id = history.start_record(["env_model.zip", "mcu.zip"], "测试员")
        assert record_id > 0

    def test_finish_record_success(self):
        """测试完成记录（成功）"""
        history = DeployHistory()
        record_id = history.start_record(["env_model.zip"])
        history.finish_record(record_id, "success")
        detail = history.get_record_detail(record_id)
        assert detail["status"] == "success"
        assert detail["total_duration_sec"] is not None

    def test_finish_record_failed(self):
        """测试完成记录（失败）"""
        history = DeployHistory()
        record_id = history.start_record(["env_model.zip"])
        history.finish_record(record_id, "failed", "连接超时")
        detail = history.get_record_detail(record_id)
        assert detail["status"] == "failed"
        assert "连接超时" in detail["error_message"]

    def test_get_recent_records(self):
        """测试获取最近记录"""
        history = DeployHistory()
        history.start_record(["pkg1.zip"])
        history.start_record(["pkg2.zip"])
        records = history.get_recent_records(10)
        assert len(records) == 2

    def test_get_statistics(self):
        """测试统计信息"""
        history = DeployHistory()
        r1 = history.start_record(["pkg1.zip"])
        history.finish_record(r1, "success")
        r2 = history.start_record(["pkg2.zip"])
        history.finish_record(r2, "failed", "错误")
        stats = history.get_statistics(30)
        assert stats["total"] == 2
        assert stats["success"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 50.0

    def test_export_report(self):
        """测试导出报告"""
        history = DeployHistory()
        r1 = history.start_record(["pkg1.zip"])
        history.finish_record(r1, "success")
        report = history.export_report(30)
        assert "# 部署报告" in report
        assert "概览" in report

    def test_update_package_status(self):
        """测试更新包状态"""
        history = DeployHistory()
        record_id = history.start_record(["env_model.zip", "mcu.zip"])
        history.update_package_status(record_id, "env_model.zip", "success", 30.5)
        detail = history.get_record_detail(record_id)
        pkg = [p for p in detail["packages_detail"] if p["package_name"] == "env_model.zip"][0]
        assert pkg["status"] == "success"
        assert pkg["duration_sec"] == 30.5

    def test_record_with_template(self):
        """测试带模板名的记录"""
        history = DeployHistory()
        record_id = history.start_record(["pkg.zip"], template_name="车间A模板")
        detail = history.get_record_detail(record_id)
        assert detail["template_name"] == "车间A模板"

    def test_record_with_device_ip(self):
        """测试带设备IP的记录"""
        history = DeployHistory()
        record_id = history.start_record(["pkg.zip"], device_ip="192.168.1.100")
        detail = history.get_record_detail(record_id)
        assert detail["device_ip"] == "192.168.1.100"
