# backend/tests/test_recommendations.py
import pytest
from app.models.project import Project
from app.models.user import User


class TestRecommendationEngine:
    """测试推荐引擎"""

    def test_recommend_based_on_history(self, test_db):
        """测试基于历史的推荐"""
        from app.services.recommendations.engine import RecommendationEngine

        user = User(username="testuser", email="test@example.com", hashed_password="hash", role="viewer")
        test_db.add(user)
        test_db.commit()

        # 创建历史项目
        for i in range(10):
            project = Project(
                title=f"Tech Video {i}",
                topic_source="tech",
                topic_title=f"AI Technology {i}",
                owner_id=user.id
            )
            test_db.add(project)
        test_db.commit()

        engine = RecommendationEngine()
        recommendations = engine.recommend_topics(user.id, test_db, limit=5)

        assert len(recommendations) <= 5

    def test_recommend_popular_topics(self, test_db):
        """测试热门话题推荐"""
        from app.services.recommendations.engine import RecommendationEngine

        user = User(username="testuser2", email="test2@example.com", hashed_password="hash", role="viewer")
        test_db.add(user)
        test_db.commit()

        # 创建不同热度的项目
        for i in range(5):
            project = Project(
                title=f"Popular Topic {i}",
                topic_hot_score=100 - i * 10,  # 递减热度
                owner_id=user.id
            )
            test_db.add(project)
        test_db.commit()

        engine = RecommendationEngine()
        popular = engine.get_popular_topics(test_db, limit=3)

        assert len(popular) <= 3
        # 应按热度排序
        if len(popular) > 1:
            assert popular[0]["hot_score"] >= popular[-1]["hot_score"]

    def test_recommend_similar_projects(self, test_db):
        """测试相似项目推荐"""
        from app.services.recommendations.engine import RecommendationEngine

        user = User(username="testuser3", email="test3@example.com", hashed_password="hash", role="viewer")
        test_db.add(user)
        test_db.commit()

        # 创建项目
        project1 = Project(
            title="Python Tutorial",
            topic_source="tech",
            topic_title="Python Programming",
            owner_id=user.id
        )
        project2 = Project(
            title="Python Advanced",
            topic_source="tech",
            topic_title="Advanced Python",
            owner_id=user.id
        )
        project3 = Project(
            title="Cooking Show",
            topic_source="lifestyle",
            topic_title="Home Cooking",
            owner_id=user.id
        )
        test_db.add_all([project1, project2, project3])
        test_db.commit()

        engine = RecommendationEngine()
        similar = engine.find_similar_projects(project1.id, test_db, limit=2)

        # 应该推荐相似的项目
        assert len(similar) <= 2
        # Cooking项目不应出现在Python项目的推荐中
        similar_ids = [p.id for p in similar]
        assert project3.id not in similar_ids


class TestRecommendationsAPI:
    """测试推荐API"""

    def test_get_topic_recommendations(self, client, test_db, admin_token, admin_user):
        """测试获取话题推荐"""
        # 创建历史项目
        for i in range(5):
            project = Project(
                title=f"Tech Video {i}",
                topic_source="tech",
                topic_title=f"AI Technology {i}",
                owner_id=admin_user.id
            )
            test_db.add(project)
        test_db.commit()

        response = client.get(
            "/api/recommendations/topics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_similar_projects(self, client, test_db, admin_token, admin_user):
        """测试获取相似项目推荐"""
        project1 = Project(title="Test Project", owner_id=admin_user.id, topic_source="tech")
        test_db.add(project1)
        test_db.commit()

        response = client.get(
            f"/api/recommendations/similar/{project1.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
