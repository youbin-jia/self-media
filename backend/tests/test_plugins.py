# backend/tests/test_plugins.py
import pytest
from sqlalchemy.exc import IntegrityError


class TestPluginDiscovery:
    """测试插件发现机制"""

    def test_discover_plugins_in_directory(self, test_db):
        """测试发现目录中的插件"""
        import os
        from app.services.plugins.discovery import PluginDiscovery

        # Get project root (one level up from backend/)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        plugins_dir = os.path.join(project_root, "plugins")

        discovery = PluginDiscovery(plugins_dir)
        plugins = discovery.discover_plugins()

        # 应该至少发现 example_source 插件
        assert len(plugins) >= 1
        assert any(p["name"] == "example_source" for p in plugins)

    def test_load_plugin_class(self, test_db):
        """测试加载插件类"""
        from app.services.plugins.loader import PluginLoader

        loader = PluginLoader()

        # 模拟插件信息
        plugin_info = {
            "module_path": "plugins.material_sources.example_source",
            "class_name": "ExampleMaterialSource"
        }

        plugin_class = loader.load_plugin_class(plugin_info)

        assert plugin_class is not None
        assert hasattr(plugin_class, 'name')
        assert hasattr(plugin_class, 'collect')

    def test_register_plugin_in_database(self, test_db):
        """测试在数据库中注册插件"""
        from app.services.plugins.discovery import PluginDiscovery
        from app.services.plugins.loader import PluginLoader
        from app.models.plugin import Plugin

        discovery = PluginDiscovery("plugins")
        loader = PluginLoader()

        # 发现并注册插件
        discovered = discovery.discover_plugins()

        if discovered:
            plugin_info = discovered[0]
            loader.register_plugin(plugin_info, test_db)

            # 验证数据库中有该插件
            plugin = test_db.query(Plugin).filter(
                Plugin.name == plugin_info["name"]
            ).first()

            assert plugin is not None

    def test_discovery_nonexistent_directory(self, test_db):
        """测试发现不存在的目录"""
        from app.services.plugins.discovery import PluginDiscovery

        discovery = PluginDiscovery("/nonexistent/path/plugins")
        plugins = discovery.discover_plugins()

        # 应该返回空列表而不是报错
        assert plugins == []


class TestMaterialSourcePlugin:
    """测试素材源插件基类"""

    def test_plugin_base_class(self):
        """测试插件基类"""
        from plugins.material_sources.base import MaterialSourcePlugin

        class TestSource(MaterialSourcePlugin):
            name = "test"
            version = "1.0.0"

            async def collect(self, keyword, count):
                return [{"url": "http://example.com/image.jpg"}]

        source = TestSource()
        assert source.name == "test"
        assert source.version == "1.0.0"

    def test_plugin_configure(self):
        """测试插件配置"""
        from plugins.material_sources.base import MaterialSourcePlugin

        class TestSource(MaterialSourcePlugin):
            name = "test"
            version = "1.0.0"

            async def collect(self, keyword, count):
                return []

        source = TestSource()
        source.configure({"api_key": "test_key"})

        assert source.config["api_key"] == "test_key"

    def test_plugin_get_metadata(self):
        """测试获取插件元数据"""
        from plugins.material_sources.base import MaterialSourcePlugin

        class TestSource(MaterialSourcePlugin):
            name = "test_source"
            version = "2.0.0"
            description = "Test description"
            author = "Test Author"
            supported_types = ["image", "video"]

            async def collect(self, keyword, count):
                return []

        source = TestSource()
        metadata = source.get_metadata()

        assert metadata["name"] == "test_source"
        assert metadata["version"] == "2.0.0"
        assert metadata["description"] == "Test description"
        assert metadata["author"] == "Test Author"
        assert metadata["supported_types"] == ["image", "video"]


class TestPluginModel:
    """测试Plugin模型"""

    def test_plugin_creation(self, test_db):
        """测试Plugin创建"""
        from app.models.plugin import Plugin

        plugin = Plugin(
            name="test_plugin",
            type="material_source",
            version="1.0.0",
            description="Test plugin",
            author="Developer",
            enabled=True
        )
        test_db.add(plugin)
        test_db.commit()

        assert plugin.id is not None
        assert plugin.name == "test_plugin"
        assert plugin.type == "material_source"
        assert plugin.enabled is True

    def test_plugin_name_unique(self, test_db):
        """测试Plugin name唯一约束"""
        from app.models.plugin import Plugin

        plugin1 = Plugin(name="unique_plugin", type="test", version="1.0.0")
        test_db.add(plugin1)
        test_db.commit()

        plugin2 = Plugin(name="unique_plugin", type="test", version="2.0.0")
        test_db.add(plugin2)

        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_plugin_configuration_creation(self, test_db):
        """测试PluginConfiguration创建"""
        from app.models.plugin import Plugin, PluginConfiguration

        plugin = Plugin(name="config_test", type="test", version="1.0.0")
        test_db.add(plugin)
        test_db.commit()

        config = PluginConfiguration(
            plugin_id=plugin.id,
            key="api_key",
            value="secret_key_123"
        )
        test_db.add(config)
        test_db.commit()

        assert config.id is not None
        assert config.plugin_id == plugin.id
        assert config.key == "api_key"

    def test_plugin_metadata(self, test_db):
        """测试Plugin metadata存储"""
        from app.models.plugin import Plugin

        plugin = Plugin(
            name="metadata_test",
            type="test",
            version="1.0.0",
            plugin_metadata={
                "website": "https://example.com",
                "repository": "https://github.com/example/plugin"
            }
        )
        test_db.add(plugin)
        test_db.commit()

        assert plugin.plugin_metadata["website"] == "https://example.com"
        assert plugin.plugin_metadata["repository"] == "https://github.com/example/plugin"


class TestPluginAPI:
    """测试Plugin API"""

    def test_list_plugins(self, client, test_db, admin_token):
        """测试列出插件"""
        from app.models.plugin import Plugin

        plugin = Plugin(name="list_test", type="test", version="1.0.0")
        test_db.add(plugin)
        test_db.commit()

        response = client.get(
            "/api/plugins",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(p["name"] == "list_test" for p in data)

    def test_get_plugin(self, client, test_db, admin_token):
        """测试获取单个插件"""
        from app.models.plugin import Plugin

        plugin = Plugin(name="get_test", type="test", version="1.0.0")
        test_db.add(plugin)
        test_db.commit()

        response = client.get(
            f"/api/plugins/{plugin.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "get_test"
        assert data["version"] == "1.0.0"

    def test_enable_plugin(self, client, test_db, admin_token):
        """测试启用插件"""
        from app.models.plugin import Plugin

        plugin = Plugin(name="enable_test", type="test", version="1.0.0", enabled=False)
        test_db.add(plugin)
        test_db.commit()

        response = client.post(
            f"/api/plugins/{plugin.id}/enable",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True

    def test_disable_plugin(self, client, test_db, admin_token):
        """测试禁用插件"""
        from app.models.plugin import Plugin

        plugin = Plugin(name="disable_test", type="test", version="1.0.0", enabled=True)
        test_db.add(plugin)
        test_db.commit()

        response = client.post(
            f"/api/plugins/{plugin.id}/disable",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    def test_update_plugin_config(self, client, test_db, admin_token):
        """测试更新插件配置"""
        from app.models.plugin import Plugin

        plugin = Plugin(name="config_update_test", type="test", version="1.0.0")
        test_db.add(plugin)
        test_db.commit()

        response = client.put(
            f"/api/plugins/{plugin.id}/config",
            json={"configurations": {"api_key": "new_key", "timeout": "30"}},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_plugin_not_found(self, client, admin_token):
        """测试插件不存在"""
        response = client.get(
            "/api/plugins/nonexistent-id",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 404
