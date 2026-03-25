# backend/app/services/hot_topic_fetcher.py
"""Hot Topic Fetcher Service - Integrates with DailyHotApi"""
import httpx
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.config import settings
from app.models.topic import Topic

logger = logging.getLogger(__name__)

# Platform display names
PLATFORM_NAMES = {
    "weibo": "微博",
    "douyin": "抖音",
    "bilibili": "B站",
    "zhihu": "知乎",
    "zhihu-daily": "知乎日报",
    "baidu": "百度",
    "toutiao": "今日头条",
    "kuaishou": "快手",
    "tieba": "贴吧",
    "douban-group": "豆瓣小组",
    "douban-movie": "豆瓣电影",
    "juejin": "掘金",
    "v2ex": "V2EX",
    "hupu": "虎扑",
    "ithome": "IT之家",
    "36kr": "36氪",
    "huxiu": "虎嗅",
    "csdn": "CSDN",
    "github": "GitHub",
    "weixin": "微信",
    "xiaohongshu": "小红书",
}


class HotTopicFetcher:
    """Service for fetching hot topics from DailyHotApi"""

    def __init__(self, api_url: Optional[str] = None, timeout: int = 30):
        self.api_url = api_url or settings.DAILYHOT_API_URL
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def fetch_platform(self, platform: str) -> List[Dict[str, Any]]:
        """
        Fetch hot topics from a specific platform

        Args:
            platform: Platform identifier (e.g., 'weibo', 'douyin')

        Returns:
            List of topic dictionaries
        """
        try:
            url = f"{self.api_url}/{platform}"
            logger.info(f"Fetching topics from {url}")

            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()

            # DailyHotApi returns data in different formats depending on platform
            # Common structure: { "code": 200, "message": "...", "data": [...] }
            if isinstance(data, dict):
                if data.get("code") == 200 or "data" in data:
                    topics = data.get("data", [])
                else:
                    logger.warning(f"Unexpected response format from {platform}: {data}")
                    topics = []
            elif isinstance(data, list):
                topics = data
            else:
                topics = []

            return self._normalize_topics(topics, platform)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {platform}: {e}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Request error fetching {platform}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching {platform}: {e}")
            return []

    def _normalize_topics(self, raw_topics: List[Dict], platform: str) -> List[Dict[str, Any]]:
        """
        Normalize topic data from different platforms to a standard format

        Args:
            raw_topics: Raw topic data from API
            platform: Source platform identifier

        Returns:
            List of normalized topic dictionaries
        """
        normalized = []

        for i, topic in enumerate(raw_topics):
            try:
                # Handle different data structures from different platforms
                normalized_topic = {
                    "title": self._extract_title(topic),
                    "source": platform,
                    "hot_score": self._extract_hot_score(topic),
                    "url": topic.get("url") or topic.get("link") or "",
                    "mobile_url": topic.get("mobileUrl") or topic.get("mobile_url") or "",
                    "category": topic.get("category") or "",
                    "cover": topic.get("cover") or topic.get("pic") or topic.get("thumbnail") or "",
                    "author": topic.get("author") or topic.get("name") or topic.get("owner") or "",
                    "original_timestamp": self._extract_timestamp(topic),
                    "raw_data": topic,
                    "fetched_at": datetime.utcnow(),
                }

                # Only add if we have a valid title
                if normalized_topic["title"]:
                    normalized.append(normalized_topic)
            except Exception as e:
                logger.warning(f"Error normalizing topic {i} from {platform}: {e}")
                continue

        return normalized

    def _extract_title(self, topic: Dict) -> str:
        """Extract title from topic data"""
        # Try common title field names
        for field in ["title", "name", "text", "keyword", "desc"]:
            if topic.get(field):
                return str(topic[field])[:500]  # Limit title length
        return ""

    def _extract_hot_score(self, topic: Dict) -> int:
        """Extract hot score from topic data"""
        # Try common hot score field names
        for field in ["hot", "hotScore", "hot_score", "heat", "score", "rank", "playCount", "view"]:
            value = topic.get(field)
            if value is not None:
                try:
                    # Handle string numbers and floats
                    if isinstance(value, str):
                        # Remove non-numeric characters except digits
                        value = ''.join(c for c in value if c.isdigit() or c == '.')
                        if value:
                            return int(float(value))
                    else:
                        return int(value)
                except (ValueError, TypeError):
                    continue
        return 0

    def _extract_timestamp(self, topic: Dict) -> Optional[int]:
        """Extract original timestamp from topic data (milliseconds)"""
        for field in ["timestamp", "createTime", "created_at", "pubDate", "publishTime", "time"]:
            value = topic.get(field)
            if value is not None:
                try:
                    if isinstance(value, (int, float)):
                        # If it's a small number, it might be seconds, convert to milliseconds
                        if value < 10000000000:
                            return int(value * 1000)
                        return int(value)
                    elif isinstance(value, str):
                        # Try to parse ISO format or other formats
                        pass
                except (ValueError, TypeError):
                    continue
        return None

    async def fetch_all_platforms(self, platforms: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        """
        Fetch topics from all specified platforms

        Args:
            platforms: List of platform identifiers, defaults to settings

        Returns:
            Dictionary mapping platform to list of topics
        """
        if platforms is None:
            platforms = [p.strip() for p in settings.TOPIC_PLATFORMS.split(",") if p.strip()]

        results = {}
        for platform in platforms:
            # 特殊处理小红书
            if platform == "xiaohongshu":
                try:
                    from app.services.xiaohongshu_fetcher import get_xiaohongshu_fetcher
                    xhs_fetcher = get_xiaohongshu_fetcher()
                    topics = await xhs_fetcher.fetch_hot_topics()
                    results[platform] = topics
                    logger.info(f"Fetched {len(topics)} topics from {platform}")
                except Exception as e:
                    logger.error(f"Error fetching xiaohongshu: {e}")
                    results[platform] = []
            else:
                topics = await self.fetch_platform(platform)
                results[platform] = topics
                logger.info(f"Fetched {len(topics)} topics from {platform}")

        return results

    def save_topics(self, db: Session, topics: List[Dict[str, Any]], platform: str) -> int:
        """
        Save topics to database, replacing existing ones for the platform

        Args:
            db: Database session
            topics: List of normalized topic dictionaries
            platform: Source platform

        Returns:
            Number of topics saved
        """
        try:
            # Delete existing topics for this platform
            db.execute(delete(Topic).where(Topic.source == platform))

            # Create new topic records
            for topic_data in topics:
                topic = Topic(**topic_data)
                db.add(topic)

            db.commit()
            logger.info(f"Saved {len(topics)} topics for {platform}")
            return len(topics)

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving topics for {platform}: {e}")
            return 0

    async def fetch_and_save(self, db: Session, platforms: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Fetch topics from platforms and save to database

        Args:
            db: Database session
            platforms: List of platform identifiers

        Returns:
            Dictionary with counts per platform
        """
        all_topics = await self.fetch_all_platforms(platforms)
        results = {}

        for platform, topics in all_topics.items():
            count = self.save_topics(db, topics, platform)
            results[platform] = count

        return results

    @staticmethod
    def get_supported_platforms() -> List[Dict[str, str]]:
        """
        Get list of supported platforms with display names

        Returns:
            List of platform info dictionaries
        """
        return [
            {"id": pid, "name": name}
            for pid, name in PLATFORM_NAMES.items()
        ]


# Singleton instance for convenience
_fetcher: Optional[HotTopicFetcher] = None


def get_fetcher() -> HotTopicFetcher:
    """Get or create the HotTopicFetcher singleton"""
    global _fetcher
    if _fetcher is None:
        _fetcher = HotTopicFetcher()
    return _fetcher
