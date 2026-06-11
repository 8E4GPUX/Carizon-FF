"""
部署模板管理模块
支持模板的保存、加载、导入导出
"""
import os
import json
import shutil
from datetime import datetime
from utils.logger import get_logger

logger = get_logger()

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "templates")


def _ensure_dir():
    os.makedirs(TEMPLATE_DIR, exist_ok=True)


class DeployTemplate:
    """部署模板"""

    def __init__(self, name: str, config: dict = None,
                 packages: list = None, cleanup_paths: list = None,
                 description: str = ""):
        self.name = name
        self.config = config or {}
        self.packages = packages or []
        self.cleanup_paths = cleanup_paths or []
        self.description = description
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.updated_at = self.created_at

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "config": self.config,
            "packages": self.packages,
            "cleanup_paths": self.cleanup_paths,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeployTemplate":
        t = cls(data["name"], data.get("config", {}),
                data.get("packages", []), data.get("cleanup_paths", []),
                data.get("description", ""))
        t.created_at = data.get("created_at", t.created_at)
        t.updated_at = data.get("updated_at", t.updated_at)
        return t


class TemplateManager:
    """模板管理器（单例）"""

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
        _ensure_dir()

    def _get_path(self, name: str) -> str:
        return os.path.join(TEMPLATE_DIR, f"{name}.json")

    def save(self, template: DeployTemplate) -> bool:
        """保存模板"""
        try:
            path = self._get_path(template.name)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"模板已保存: {template.name}")
            return True
        except Exception as e:
            logger.error(f"保存模板失败: {e}")
            return False

    def load(self, name: str) -> DeployTemplate:
        """加载模板"""
        try:
            path = self._get_path(name)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return DeployTemplate.from_dict(data)
        except Exception as e:
            logger.error(f"加载模板失败: {e}")
            return None

    def delete(self, name: str) -> bool:
        """删除模板"""
        try:
            path = self._get_path(name)
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"模板已删除: {name}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除模板失败: {e}")
            return False

    def list_templates(self) -> list:
        """列出所有模板"""
        _ensure_dir()
        templates = []
        for f in os.listdir(TEMPLATE_DIR):
            if f.endswith(".json"):
                try:
                    t = self.load(f[:-5])
                    if t:
                        templates.append(t)
                except:
                    pass
        return templates

    def export_template(self, name: str, export_path: str) -> bool:
        """导出模板到指定路径"""
        try:
            src = self._get_path(name)
            if os.path.exists(src):
                shutil.copy2(src, export_path)
                return True
            return False
        except Exception as e:
            logger.error(f"导出模板失败: {e}")
            return False

    def import_template(self, import_path: str) -> bool:
        """从文件导入模板"""
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            template = DeployTemplate.from_dict(data)
            return self.save(template)
        except Exception as e:
            logger.error(f"导入模板失败: {e}")
            return False
