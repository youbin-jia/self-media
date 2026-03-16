# backend/app/services/material_collector.py
"""Material Collector Service with Pexels API and Mock Data"""
import os
import httpx
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session

from app.config import settings
from app.utils.deduplication import MaterialDeduplicator


class MaterialCollector:
    """Service for collecting image/video materials from Pexels API or mock data"""

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.api_key = settings.PEXELS_API_KEY
        self.base_url = "https://api.pexels.com/v1"
        self.materials_dir = Path(settings.DATA_DIR) / "materials"
        self.deduplicator = MaterialDeduplicator()
        self._ensure_materials_dir()

    def _ensure_materials_dir(self):
        """Ensure materials directory exists"""
        self.materials_dir.mkdir(parents=True, exist_ok=True)

    async def search_images(
        self,
        query: str,
        per_page: int = 10,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Search for images using Pexels API or return mock data

        Args:
            query: Search query string
            per_page: Number of results per page
            page: Page number

        Returns:
            List of image dictionaries with metadata
        """
        if not self.api_key:
            return self._get_mock_images(query, per_page)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={
                        "query": query,
                        "per_page": per_page,
                        "page": page
                    },
                    headers={
                        "Authorization": self.api_key
                    },
                    timeout=10.0
                )

                if response.status_code != 200:
                    return self._get_mock_images(query, per_page)

                data = response.json()
                photos = data.get("photos", [])

                return [
                    {
                        "id": str(photo.get("id", uuid.uuid4())),
                        "type": "image",
                        "source": "pexels",
                        "source_url": photo.get("src", {}).get("original"),
                        "thumbnail_url": photo.get("src", {}).get("medium"),
                        "width": photo.get("width"),
                        "height": photo.get("height"),
                        "photographer": photo.get("photographer"),
                        "photographer_url": photo.get("photographer_url"),
                        "avg_color": photo.get("avg_color"),
                        "alt": photo.get("alt", query)
                    }
                    for photo in photos
                ]
        except Exception:
            # Fallback to mock data on any error
            return self._get_mock_images(query, per_page)

    async def download_material(
        self,
        source_url: str,
        project_id: str,
        material_id: str
    ) -> Optional[str]:
        """
        Download material to local storage

        Args:
            source_url: URL of the material to download
            project_id: Project ID for organizing storage
            material_id: Material ID for filename

        Returns:
            Local path to downloaded file, or None if download failed
        """
        if not self.api_key:
            # For mock mode, return a mock local path
            return str(self.materials_dir / project_id / f"{material_id}.jpg")

        try:
            # Create project-specific directory
            project_dir = self.materials_dir / project_id
            project_dir.mkdir(parents=True, exist_ok=True)

            # Download file
            local_path = project_dir / f"{material_id}.jpg"

            async with httpx.AsyncClient() as client:
                response = await client.get(source_url, timeout=30.0)

                if response.status_code != 200:
                    return None

                with open(local_path, "wb") as f:
                    f.write(response.content)

            return str(local_path)
        except Exception:
            return None

    def _get_mock_images(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Generate mock image data for testing

        Args:
            query: Search query for generating relevant mock data
            count: Number of mock images to generate

        Returns:
            List of mock image dictionaries
        """
        mock_images = []
        base_colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#FF33A8"]

        for i in range(count):
            mock_images.append({
                "id": f"mock_{uuid.uuid4().hex[:8]}",
                "type": "image",
                "source": "mock",
                "source_url": f"https://mock.pexels.com/{query.replace(' ', '-')}/{i+1}",
                "thumbnail_url": f"https://mock.pexels.com/thumb/{query.replace(' ', '-')}/{i+1}",
                "width": 1920,
                "height": 1080,
                "photographer": f"Mock Photographer {i+1}",
                "photographer_url": f"https://pexels.com/@mock{i+1}",
                "avg_color": base_colors[i % len(base_colors)],
                "alt": f"Mock image for {query} - {i+1}"
            })

        return mock_images

    def extract_keywords(self, topic_title: str, max_keywords: int = 3) -> List[str]:
        """
        Extract keywords from topic title (simplified implementation)

        Args:
            topic_title: The topic title to extract keywords from
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of keywords
        """
        # Simple implementation: split by common separators and take first N words
        separators = [" ", "-", "_", "|", ":", ";", ","]
        words = [topic_title]

        for sep in separators:
            new_words = []
            for word in words:
                new_words.extend(word.split(sep))
            words = new_words

        # Filter out empty strings and common stop words
        stop_words = {"的", "了", "是", "在", "和", "与", "或", "等", "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "and", "or"}
        keywords = [
            word.strip()
            for word in words
            if word.strip() and word.strip().lower() not in stop_words
        ]

        return keywords[:max_keywords]

    def _extract_tags(self, query: str, item: dict) -> List[str]:
        """
        Extract tags from material

        Args:
            query: Search query
            item: Material item data

        Returns:
            List of tags
        """
        tags = [query]

        # Extract from Pexels keywords if available
        if "tags" in item:
            if isinstance(item["tags"], list):
                tags.extend([tag.strip() for tag in item["tags"][:5]])
            elif isinstance(item["tags"], str):
                tags.extend([tag.strip() for tag in item["tags"].split(",")[:5]])

        # Extract from alt text
        if "alt" in item and item["alt"]:
            words = item["alt"].split()
            tags.extend([word.strip() for word in words[:3] if len(word) > 2])

        return list(set(tags))  # Remove duplicates
