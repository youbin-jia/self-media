# backend/tests/test_pwa.py
import pytest
import json
import os


def get_project_root():
    """Get project root directory"""
    # Get the directory where this test file is located
    test_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up: tests -> backend -> project_root
    return os.path.dirname(os.path.dirname(test_dir))


class TestPWASupport:
    """测试PWA支持"""

    def test_manifest_json_exists(self):
        """测试manifest.json存在"""
        project_root = get_project_root()
        manifest_path = os.path.join(project_root, "frontend/pwa/manifest.json")
        assert os.path.exists(manifest_path), f"manifest.json not found at {manifest_path}"

    def test_manifest_json_valid(self):
        """测试manifest.json格式有效"""
        project_root = get_project_root()
        manifest_path = os.path.join(project_root, "frontend/pwa/manifest.json")

        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        # 验证必需字段
        assert "name" in manifest
        assert "short_name" in manifest
        assert "start_url" in manifest
        assert "display" in manifest
        assert manifest["display"] in ["standalone", "fullscreen", "minimal-ui"]

    def test_service_worker_exists(self):
        """测试Service Worker存在"""
        project_root = get_project_root()
        sw_path = os.path.join(project_root, "frontend/pwa/sw.js")
        assert os.path.exists(sw_path), f"Service Worker not found at {sw_path}"

    def test_service_worker_has_cache_handlers(self):
        """测试Service Worker包含缓存处理"""
        project_root = get_project_root()
        sw_path = os.path.join(project_root, "frontend/pwa/sw.js")

        with open(sw_path, 'r') as f:
            content = f.read()

        # 验证包含必要的生命周期事件
        assert "install" in content
        assert "fetch" in content
        assert "activate" in content

    def test_offline_page_exists(self):
        """测试离线页面存在"""
        project_root = get_project_root()
        offline_path = os.path.join(project_root, "frontend/pwa/offline.html")
        assert os.path.exists(offline_path), f"Offline page not found at {offline_path}"

    def test_manifest_has_icons(self):
        """测试manifest包含图标配置"""
        project_root = get_project_root()
        manifest_path = os.path.join(project_root, "frontend/pwa/manifest.json")

        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        assert "icons" in manifest
        assert len(manifest["icons"]) > 0

        # 验证图标格式
        for icon in manifest["icons"]:
            assert "src" in icon
            assert "sizes" in icon
            assert "type" in icon

    def test_manifest_has_theme_color(self):
        """测试manifest包含主题色"""
        project_root = get_project_root()
        manifest_path = os.path.join(project_root, "frontend/pwa/manifest.json")

        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        assert "theme_color" in manifest
        assert "background_color" in manifest
