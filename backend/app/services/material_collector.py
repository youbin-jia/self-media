# backend/app/services/material_collector.py
"""Material Collector Service with Pexels API and Mock Data"""
import os
import httpx
import uuid
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session

from app.config import settings
from app.utils.deduplication import MaterialDeduplicator

logger = logging.getLogger(__name__)


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
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error searching Pexels for '{query}': {e.response.status_code}")
            return self._get_mock_images(query, per_page)
        except httpx.RequestError as e:
            logger.warning(f"Network error searching Pexels for '{query}': {str(e)}")
            return self._get_mock_images(query, per_page)
        except Exception as e:
            logger.error(f"Unexpected error searching Pexels for '{query}': {str(e)}", exc_info=True)
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
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading material from {source_url}: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Network error downloading material from {source_url}: {str(e)}")
            return None
        except IOError as e:
            logger.error(f"File I/O error saving material to {local_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading material from {source_url}: {str(e)}", exc_info=True)
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

    async def collect_with_deduplication(
        self,
        query: str,
        project_id: str,
        count: int = 10,
        skip_duplicate: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Collect materials with deduplication support

        Args:
            query: Search query
            project_id: Project ID
            count: Number of materials to collect
            skip_duplicate: Whether to skip duplicates

        Returns:
            List of collected materials (as dictionaries)

        Raises:
            ValueError: If database session not initialized
        """
        if not self.db:
            raise ValueError("Database session required for deduplication")

        from app.models.material import Material

        # Search for images
        images = await self.search_images(query, per_page=count)

        collected = []
        for img in images:
            material_id = img.get("id") or str(uuid.uuid4())

            # Download material
            local_path = await self.download_material(
                img.get("source_url"),
                project_id,
                material_id
            )

            if not local_path:
                continue

            # Calculate file hash if file exists
            file_hash = None
            file_size = None
            if Path(local_path).exists():
                file_hash = self.deduplicator.calculate_file_hash(local_path)
                file_size = Path(local_path).stat().st_size

            # Check for duplicates if enabled
            if skip_duplicate and file_hash:
                existing = self.deduplicator.check_duplicate(
                    self.db,
                    file_hash,
                    project_id
                )
                if existing:
                    # Delete duplicate file, return existing material info
                    if Path(local_path).exists():
                        Path(local_path).unlink()

                    collected.append({
                        "id": existing.id,
                        "project_id": existing.project_id,
                        "material_type": existing.material_type,
                        "type": existing.type or existing.material_type,
                        "source": existing.source,
                        "source_id": existing.source_id,
                        "source_url": existing.source_url,
                        "local_path": existing.local_path,
                        "file_hash": existing.file_hash,
                        "duration": existing.duration,
                        "width": existing.width,
                        "height": existing.height,
                        "file_size": existing.file_size,
                        "material_metadata": existing.material_metadata,
                        "tags": existing.tags,
                        "description": existing.description,
                        "quality_score": existing.quality_score,
                        "is_used": existing.is_used,
                        "is_duplicate": True
                    })
                    continue

            # Extract tags
            tags = self._extract_tags(query, img)

            # Create new material record
            material_data = {
                "id": material_id,
                "project_id": project_id,
                "material_type": img.get("type", "image"),
                "type": img.get("type", "image"),  # Legacy field
                "source": img.get("source", "unknown"),
                "source_id": img.get("id"),
                "source_url": img.get("source_url"),
                "local_path": local_path,
                "file_hash": file_hash,
                "width": img.get("width"),
                "height": img.get("height"),
                "file_size": file_size,
                "material_metadata": {
                    "thumbnail_url": img.get("thumbnail_url"),
                    "photographer": img.get("photographer"),
                    "photographer_url": img.get("photographer_url"),
                    "avg_color": img.get("avg_color"),
                    "alt": img.get("alt")
                },
                "tags": tags,
                "description": img.get("alt", query),
                "quality_score": None,  # Can be set later by quality detector
                "is_used": False,
                "is_duplicate": False
            }

            # Create Material object
            material = Material(**material_data)
            self.db.add(material)
            self.db.flush()  # Flush to get the created_at timestamp

            # Update material_data with created_at
            material_data["created_at"] = material.created_at

            collected.append(material_data)

        # Commit all new materials
        if collected:
            self.db.commit()

        return collected
