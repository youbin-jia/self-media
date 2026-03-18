# backend/app/services/recommendations/engine.py
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.project import Project


class RecommendationEngine:
    """智能推荐引擎"""

    def recommend_topics(
        self,
        user_id: str,
        db: Session,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        基于用户历史推荐话题

        Args:
            user_id: 用户ID
            db: 数据库会话
            limit: 返回数量限制

        Returns:
            推荐话题列表
        """
        # 分析用户历史项目的主题来源
        user_topics = db.query(
            Project.topic_source,
            Project.topic_title,
            func.count(Project.id).label('count')
        ).filter(
            Project.owner_id == user_id,
            Project.topic_source.isnot(None)
        ).group_by(
            Project.topic_source,
            Project.topic_title
        ).order_by(
            desc('count')
        ).limit(10).all()

        if not user_topics:
            # 如果没有历史，返回热门话题
            return self.get_popular_topics(db, limit)

        # 基于用户偏好生成推荐
        recommendations = []
        seen_titles = set()

        for topic in user_topics:
            if topic.topic_title and topic.topic_title not in seen_titles:
                recommendations.append({
                    "topic_source": topic.topic_source,
                    "topic_title": topic.topic_title,
                    "relevance_score": topic.count / 10.0  # 归一化
                })
                seen_titles.add(topic.topic_title)

                if len(recommendations) >= limit:
                    break

        return recommendations

    def get_popular_topics(
        self,
        db: Session,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取热门话题

        Args:
            db: 数据库会话
            limit: 返回数量限制

        Returns:
            热门话题列表
        """
        # 按热度分数获取热门项目
        popular_projects = db.query(Project).filter(
            Project.topic_hot_score.isnot(None)
        ).order_by(
            desc(Project.topic_hot_score)
        ).limit(limit).all()

        topics = []
        seen_titles = set()

        for project in popular_projects:
            if project.topic_title and project.topic_title not in seen_titles:
                topics.append({
                    "topic_source": project.topic_source,
                    "topic_title": project.topic_title,
                    "hot_score": project.topic_hot_score
                })
                seen_titles.add(project.topic_title)

        return topics

    def find_similar_projects(
        self,
        project_id: str,
        db: Session,
        limit: int = 5
    ) -> List[Project]:
        """
        查找相似项目

        Args:
            project_id: 项目ID
            db: 数据库会话
            limit: 返回数量限制

        Returns:
            相似项目列表
        """
        # 获取当前项目
        project = db.query(Project).filter(Project.id == project_id).first()

        if not project:
            return []

        # 基于主题来源查找相似项目
        similar = db.query(Project).filter(
            Project.id != project_id,
            Project.topic_source == project.topic_source
        ).limit(limit).all()

        return similar
