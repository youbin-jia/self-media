from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import hashlib
import logging
from sqlalchemy.orm import Session
from app.models.material import Material

logger = logging.getLogger(__name__)


class MaterialDeduplicator:
    """Material deduplication utility"""

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """
        Calculate SHA256 hash of a file

        Args:
            file_path: Path to the file

        Returns:
            SHA256 hash as hex string

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read
        """
        try:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except IOError as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise IOError(f"Failed to read file for hashing: {file_path}") from e

    @staticmethod
    def check_duplicate(db: Session, file_hash: str, project_id: Optional[str] = None) -> Optional[Material]:
        """
        Check if material already exists
        Args:
            db: Database session
            file_hash: File hash
            project_id: Project ID (optional, for project-level deduplication)
        Returns:
            Existing material or None
        """
        query = db.query(Material).filter(Material.file_hash == file_hash)
        if project_id:
            query = query.filter(Material.project_id == project_id)
        return query.first()

    @staticmethod
    def calculate_similarity(file1_metadata: Dict[str, Any], file2_metadata: Dict[str, Any]) -> float:
        """
        Calculate material similarity based on metadata
        Args:
            file1_metadata: File 1 metadata
            file2_metadata: File 2 metadata
        Returns:
            Similarity score 0-1
        """
        # Simplified version: based on tags
        tags1 = set(file1_metadata.get("tags", []))
        tags2 = set(file2_metadata.get("tags", []))

        if not tags1 and not tags2:
            return 0.0

        # Jaccard similarity
        intersection = len(tags1 & tags2)
        union = len(tags1 | tags2)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def find_similar_materials(
        db: Session,
        material: Material,
        threshold: float = 0.7,
        limit: int = 100
    ) -> List[Tuple[Material, float]]:
        """
        Find similar materials
        Args:
            db: Database session
            material: Target material
            threshold: Similarity threshold
            limit: Maximum number of materials to compare (for performance)
        Returns:
            List of similar materials with similarity scores
        """
        # Use limit to prevent loading too many materials
        all_materials = db.query(Material).filter(
            Material.id != material.id,
            Material.material_type == material.material_type
        ).limit(limit).all()

        similar = []
        for other in all_materials:
            if material.tags and other.tags:
                similarity = MaterialDeduplicator.calculate_similarity(
                    {"tags": material.tags},
                    {"tags": other.tags}
                )
                if similarity >= threshold:
                    similar.append((other, similarity))

        return sorted(similar, key=lambda x: x[1], reverse=True)
