# backend/tests/test_batch_operations.py
import pytest
from app.models.project import Project
from app.models.material import Material
from app.models.user import User


class TestBatchProjectOperations:
    """测试项目批量操作"""

    def test_batch_delete_projects(self, client, test_db, admin_token, admin_user):
        """测试批量删除项目"""
        # 创建测试项目
        project1 = Project(title="Project 1", owner_id=admin_user.id)
        project2 = Project(title="Project 2", owner_id=admin_user.id)
        project3 = Project(title="Project 3", owner_id=admin_user.id)
        test_db.add_all([project1, project2, project3])
        test_db.commit()

        # 批量删除
        response = client.post(
            "/api/projects/batch/delete",
            json={"project_ids": [project1.id, project2.id]},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert response.json()["deleted_count"] == 2

        # 验证只剩一个项目
        remaining = test_db.query(Project).filter(Project.owner_id == admin_user.id).all()
        assert len(remaining) == 1
        assert remaining[0].id == project3.id

    def test_batch_update_project_status(self, client, test_db, admin_token, admin_user):
        """测试批量更新项目状态"""
        project1 = Project(title="Project 1", owner_id=admin_user.id, status="draft")
        project2 = Project(title="Project 2", owner_id=admin_user.id, status="draft")
        test_db.add_all([project1, project2])
        test_db.commit()

        # 批量更新
        response = client.post(
            "/api/projects/batch/update-status",
            json={"project_ids": [project1.id, project2.id], "status": "active"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert response.json()["updated_count"] == 2

        # 验证状态已更新
        test_db.refresh(project1)
        test_db.refresh(project2)
        assert project1.status == "active"
        assert project2.status == "active"

    def test_batch_operation_with_nonexistent_ids(self, client, test_db, admin_token):
        """测试包含不存在ID的批量操作"""
        response = client.post(
            "/api/projects/batch/delete",
            json={"project_ids": ["nonexistent-id-1", "nonexistent-id-2"]},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert response.json()["deleted_count"] == 0

    def test_batch_operation_empty_ids(self, client, test_db, admin_token):
        """测试空ID列表的批量操作"""
        response = client.post(
            "/api/projects/batch/delete",
            json={"project_ids": []},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 400
