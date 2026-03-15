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
                "id": "topic-1",
                "title": "AI技术突破：GPT-5即将发布",
                "source": "weibo",
                "hot_score": 9875432,
                "category": "科技",
                "url": "https://weibo.com/topic/ai-gpt5",
                "fetched_at": datetime.now().isoformat(),
            },
            {
                "id": "topic-2",
                "title": "春节档电影票房破纪录",
                "source": "douyin",
                "hot_score": 8234567,
                "category": "娱乐",
                "url": "https://douyin.com/topic/spring-movies",
                "fetched_at": datetime.now().isoformat(),
            },
            {
                "id": "topic-3",
                "title": "新能源汽车销量创新高",
                "source": "toutiao",
                "hot_score": 6543210,
                "category": "汽车",
                "url": "https://toutiao.com/topic/nev-sales",
                "fetched_at": datetime.now().isoformat(),
            },
            {
                "id": "topic-4",
                "title": "国产游戏《黑神话：悟空》获国际大奖",
                "source": "bilibili",
                "hot_score": 5432109,
                "category": "游戏",
                "url": "https://bilibili.com/topic/black-myth",
                "fetched_at": datetime.now().isoformat(),
            },
            {
                "id": "topic-5",
                "title": "春节消费市场回暖明显",
                "source": "weibo",
                "hot_score": 4321098,
                "category": "财经",
                "url": "https://weibo.com/topic/spring-consumption",
                "fetched_at": datetime.now().isoformat(),
            },
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
            topic["fetched_at"] = datetime.now().isoformat()

        return {
            "status": "success",
            "message": f"Refreshed {len(self.mock_topics)} topics",
            "timestamp": datetime.now().isoformat()
        }
