# backend/app/services/topic_monitor.py
"""Topic Monitor Service with Mock Data"""
import random
from typing import List, Optional
from datetime import datetime


class TopicMonitor:
    """Service for monitoring hot topics across platforms"""

    def __init__(self):
        self.mock_topics = [
            {
                "id": "topic_1",
                "title": "AI技术突破：GPT-5即将发布",
                "source": "weibo",
                "hot_score": 98,
                "category": "科技",
                "url": "https://weibo.com/hot/1",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "topic_2",
                "title": "新能源汽车销量创新高",
                "source": "zhihu",
                "hot_score": 95,
                "category": "财经",
                "url": "https://zhihu.com/hot/2",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "topic_3",
                "title": "全国两会重要议题解读",
                "source": "baidu",
                "hot_score": 92,
                "category": "时政",
                "url": "https://baidu.com/hot/3",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "topic_4",
                "title": "教育改革新政策出台",
                "source": "toutiao",
                "hot_score": 88,
                "category": "教育",
                "url": "https://toutiao.com/hot/4",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "topic_5",
                "title": "春季养生健康指南",
                "source": "weibo",
                "hot_score": 85,
                "category": "健康",
                "url": "https://weibo.com/hot/5",
                "created_at": datetime.now().isoformat()
            }
        ]

    async def fetch_topics(
        self,
        source: Optional[str] = None,
        limit: int = 20
    ) -> List[dict]:
        """
        Fetch topics from mock data

        Args:
            source: Optional source filter (weibo, douyin, toutiao, bilibili)
            limit: Maximum number of topics to return

        Returns:
            List of topic dictionaries
        """
        topics = self.mock_topics

        if source:
            topics = [t for t in topics if t["source"] == source]

        # Sort by hot_score descending
        topics = sorted(topics, key=lambda x: x["hot_score"], reverse=True)

        return topics[:limit]

    async def refresh_topics(self) -> dict:
        """
        Refresh topics by randomly adjusting hot scores

        Returns:
            Status dict with refresh result
        """
        for topic in self.mock_topics:
            # Randomly adjust hot_score by -10% to +10%
            change = random.uniform(-0.1, 0.1)
            topic["hot_score"] = int(topic["hot_score"] * (1 + change))
            topic["created_at"] = datetime.now().isoformat()

        return {
            "status": "success",
            "message": f"Refreshed {len(self.mock_topics)} topics",
            "timestamp": datetime.now().isoformat()
        }
