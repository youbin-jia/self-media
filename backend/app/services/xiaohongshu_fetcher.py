# backend/app/services/xiaohongshu_fetcher.py
"""Xiaohongshu (小红书) Hot Topics Fetcher"""
import re
import json
import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class XiaohongshuFetcher:
    """Fetcher for Xiaohongshu (小红书) hot topics"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers=self.headers,
            follow_redirects=True
        )

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def fetch_hot_topics(self) -> List[Dict[str, Any]]:
        """
        Fetch hot topics from Xiaohongshu explore page

        Returns:
            List of normalized topic dictionaries
        """
        try:
            # 访问发现页面
            response = await self.client.get("https://www.xiaohongshu.com/explore")
            response.raise_for_status()

            html = response.text

            # 从页面中提取 __INITIAL_STATE__ 数据
            # 使用更宽松的正则匹配，直到 </script> 标签
            match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>', html, re.DOTALL)
            if not match:
                logger.warning("Could not find __INITIAL_STATE__ in Xiaohongshu page")
                return []

            # 解析 JSON
            try:
                json_str = match.group(1)
                # 尝试找到有效的 JSON 结束位置
                # JSON 可能包含未转义的字符，需要处理
                data = self._parse_json_with_recovery(json_str)
            except Exception as e:
                logger.error(f"Failed to parse Xiaohongshu data: {e}")
                return []

            # 提取热门笔记
            topics = []

            # 尝试从不同的数据结构中获取
            feeds = None

            # 尝试多种路径获取 feeds
            paths = [
                ("feed", "feeds"),  # 主要路径
                ("homeFeed", "feeds"),
                ("explore", "feeds"),
                ("feeds",),
                ("homeFeed", "firstNotesFeed", "notes"),
                ("exploreNotes", "notes"),
                ("search", "feeds"),
            ]

            for path in paths:
                current = data
                for key in path:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        current = None
                        break
                if current and isinstance(current, list) and len(current) > 0:
                    feeds = current
                    logger.debug(f"Found feeds at path: {'.'.join(path)}")
                    break

            if not feeds:
                logger.warning("No feeds found in Xiaohongshu data")
                return []

            for item in feeds[:50]:  # 限制50条
                try:
                    # 小红书的结构是 item.noteCard
                    note_card = item.get("noteCard", {})
                    if not note_card:
                        continue

                    topic = self._normalize_note_card(note_card, item.get("id", ""))
                    if topic:
                        topics.append(topic)
                except Exception as e:
                    logger.debug(f"Error processing item: {e}")
                    continue

            logger.info(f"Fetched {len(topics)} topics from Xiaohongshu")
            return topics

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching Xiaohongshu: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching Xiaohongshu: {e}")
            return []

    def _parse_json_with_recovery(self, json_str: str) -> Dict:
        """Parse JSON with error recovery for malformed JSON"""
        import json

        # 替换 JavaScript 的 undefined 为 JSON 的 null
        json_str = re.sub(r'\bundefined\b', 'null', json_str)

        # 首先尝试直接解析
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # 尝试找到最后一个有效的闭合括号
        # 计算括号平衡
        brace_count = 0
        bracket_count = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(json_str):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # 找到最外层闭合
                    try:
                        return json.loads(json_str[:i+1])
                    except:
                        continue
            elif char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1

        # 最后尝试：截断到最后一个有效的闭合位置
        raise json.JSONDecodeError("Could not parse JSON", json_str, 0)

    def _normalize_note_card(self, note_card: Dict, note_id: str = "") -> Optional[Dict[str, Any]]:
        """Normalize a Xiaohongshu note card to standard topic format"""
        try:
            title = note_card.get("displayTitle", "")
            if not title:
                return None

            # 获取点赞数作为热度
            interact_info = note_card.get("interactInfo", {})
            like_count_str = interact_info.get("likedCount", "0")
            like_count = self._parse_chinese_number(like_count_str)

            # 获取作者信息
            user = note_card.get("user", {})
            author = user.get("nickname", "") or user.get("name", "")

            # 获取封面图
            cover_info = note_card.get("cover", {})
            cover = cover_info.get("urlDefault", "") or cover_info.get("url", "")

            # 构建链接
            if note_id:
                url = f"https://www.xiaohongshu.com/explore/{note_id}"
            else:
                url = "https://www.xiaohongshu.com/explore"

            return {
                "title": title[:500],
                "source": "xiaohongshu",
                "hot_score": like_count,
                "url": url,
                "mobile_url": url,
                "category": note_card.get("type", ""),
                "cover": cover,
                "author": author,
                "original_timestamp": None,
                "raw_data": note_card,
                "fetched_at": datetime.utcnow(),
            }
        except Exception as e:
            logger.debug(f"Error normalizing note card: {e}")
            return None

    def _parse_chinese_number(self, num_str: str) -> int:
        """Parse Chinese number format like '2.2万' to integer"""
        if not num_str:
            return 0

        num_str = str(num_str).strip()

        # Handle Chinese units
        multipliers = {
            '万': 10000,
            '亿': 100000000,
            'w': 10000,
            'k': 1000,
        }

        for unit, mult in multipliers.items():
            if unit in num_str:
                try:
                    num = float(num_str.replace(unit, ''))
                    return int(num * mult)
                except ValueError:
                    continue

        # Try parsing as regular number
        try:
            # Remove commas and other non-numeric chars
            num_str = ''.join(c for c in num_str if c.isdigit() or c == '.')
            if num_str:
                return int(float(num_str))
        except ValueError:
            pass

        return 0

    def _normalize_note(self, note: Dict) -> Optional[Dict[str, Any]]:
        """Normalize a Xiaohongshu note to standard topic format"""
        try:
            note_id = note.get("noteId", "")
            title = note.get("displayTitle", "") or note.get("title", "")
            if not title:
                return None

            # 获取点赞数作为热度
            like_count = note.get("interactInfo", {}).get("likedCount", 0)
            if isinstance(like_count, str):
                like_count = int(like_count) if like_count.isdigit() else 0

            # 获取作者信息
            user = note.get("user", {})
            author = user.get("nickname", "") or user.get("name", "")

            # 获取封面图
            cover = ""
            images = note.get("imageList", [])
            if images and len(images) > 0:
                cover = images[0].get("urlDefault", "") or images[0].get("url", "")

            # 构建链接
            url = f"https://www.xiaohongshu.com/explore/{note_id}"

            return {
                "title": title[:500],
                "source": "xiaohongshu",
                "hot_score": like_count,
                "url": url,
                "mobile_url": url,
                "category": note.get("type", ""),
                "cover": cover,
                "author": author,
                "original_timestamp": None,
                "raw_data": note,
                "fetched_at": datetime.utcnow(),
            }
        except Exception as e:
            logger.debug(f"Error normalizing note: {e}")
            return None


# Singleton instance
_fetcher: Optional[XiaohongshuFetcher] = None


def get_xiaohongshu_fetcher() -> XiaohongshuFetcher:
    """Get or create the XiaohongshuFetcher singleton"""
    global _fetcher
    if _fetcher is None:
        _fetcher = XiaohongshuFetcher()
    return _fetcher
