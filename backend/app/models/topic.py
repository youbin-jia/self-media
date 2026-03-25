# backend/app/models/topic.py
"""Topic model for caching hot topics from various platforms"""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Index, BigInteger
from sqlalchemy.sql import func
from app.database import Base


class Topic(Base):
    """Cached hot topic from social media platforms"""
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)  # weibo, douyin, bilibili, etc.
    hot_score = Column(Integer, default=0)
    url = Column(String(1000))
    category = Column(String(50))
    mobile_url = Column(String(1000))  # 移动端链接
    cover = Column(String(1000))  # 封面图片
    author = Column(String(200))  # 作者
    original_timestamp = Column(BigInteger)  # 原始发布时间戳（毫秒）
    raw_data = Column(JSON)  # 原始数据，保留完整信息
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 复合索引：按平台和热度排序
    __table_args__ = (
        Index('ix_topics_source_hot', 'source', 'hot_score'),
    )

    def __repr__(self):
        return f"<Topic(id={self.id}, title={self.title[:30]}, source={self.source}, hot_score={self.hot_score})>"

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": f"topic_{self.id}",
            "title": self.title,
            "source": self.source,
            "hot_score": self.hot_score,
            "url": self.url,
            "category": self.category,
            "mobile_url": self.mobile_url,
            "cover": self.cover,
            "author": self.author,
            "original_timestamp": self.original_timestamp,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
        }
