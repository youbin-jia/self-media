# backend/tests/test_mobile.py
import pytest
from app.models.project import Project
from app.models.user import User


class TestMobileAPI:
    """测试移动端API"""

    def test_mobile_project_list_limited_fields(self, client, test_db, admin_token, admin_user):
        """测试移动端项目列表（字段精简）"""
        for i in range(5):
            project = Project(
                title=f"Project {i}",
                status="active",
                owner_id=admin_user.id
            )
            test_db.add(project)
        test_db.commit()

        # 获取移动端项目列表
        response = client.get(
            "/api/mobile/projects",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 5

        # 验证返回字段精简
        if data["items"]:
            project = data["items"][0]
            assert "id" in project
            assert "title" in project
            assert "status" in project
            # 不应包含大字段
            assert "project_metadata" not in project

    def test_mobile_project_pagination(self, client, test_db, admin_token, admin_user):
        """测试移动端分页"""
        for i in range(20):
            project = Project(title=f"Project {i}", owner_id=admin_user.id)
            test_db.add(project)
        test_db.commit()

        # 请求第一页
        response = client.get(
            "/api/mobile/projects?page=1&page_size=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 20
        assert data["page"] == 1

    def test_mobile_dashboard_summary(self, client, test_db, admin_token, admin_user):
        """测试移动端Dashboard摘要"""
        # 创建不同状态的项目
        for status in ["active", "completed", "draft"]:
            project = Project(
                title=f"Project {status}",
                status=status,
                owner_id=admin_user.id
            )
            test_db.add(project)
        test_db.commit()

        response = client.get(
            "/api/mobile/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_projects" in data
        assert "active_projects" in data
        assert "completed_projects" in data

    def test_mobile_quick_actions(self, client, test_db, admin_token, admin_user):
        """测试移动端快速操作"""
        project = Project(title="Test", status="draft", owner_id=admin_user.id)
        test_db.add(project)
        test_db.commit()

        # 快速启动项目
        response = client.post(
            f"/api/mobile/projects/{project.id}/quick-start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        # 项目状态应变为active
        test_db.refresh(project)
        assert project.status == "active"
