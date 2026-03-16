import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from app.utils.deduplication import MaterialDeduplicator
from app.models.material import Material


class TestMaterialDeduplicator:
    """测试素材去重器"""

    def test_calculate_file_hash(self, tmp_path):
        """测试文件哈希计算"""
        # Create test file
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"test content" * 100)

        hash1 = MaterialDeduplicator.calculate_file_hash(str(test_file))
        hash2 = MaterialDeduplicator.calculate_file_hash(str(test_file))

        # Same file should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_different_files_have_different_hashes(self, tmp_path):
        """不同文件产生不同哈希"""
        file1 = tmp_path / "file1.mp4"
        file1.write_bytes(b"content 1")
        file2 = tmp_path / "file2.mp4"
        file2.write_bytes(b"content 2")

        hash1 = MaterialDeduplicator.calculate_file_hash(str(file1))
        hash2 = MaterialDeduplicator.calculate_file_hash(str(file2))

        assert hash1 != hash2

    def test_check_duplicate_found(self):
        """测试检查重复素材（存在）"""
        mock_db = Mock()
        mock_material = Mock(spec=Material)
        mock_material.file_hash = "test_hash_123"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_material

        result = MaterialDeduplicator.check_duplicate(mock_db, "test_hash_123")

        assert result == mock_material

    def test_check_duplicate_not_found(self):
        """测试检查重复素材（不存在）"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = MaterialDeduplicator.check_duplicate(mock_db, "nonexistent_hash")

        assert result is None

    def test_check_duplicate_with_project_filter(self):
        """测试项目内去重"""
        mock_db = Mock()
        mock_material = Mock(spec=Material)
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_material

        result = MaterialDeduplicator.check_duplicate(
            mock_db,
            "test_hash",
            project_id="project-uuid-123"  # String type to match database schema
        )

        assert result == mock_material
        # Verify project_id filter was applied
        mock_db.query.return_value.filter.assert_called()

    def test_calculate_similarity_same_tags(self):
        """测试相似度计算（相同标签）"""
        metadata1 = {"tags": ["nature", "landscape", "sunset"]}
        metadata2 = {"tags": ["nature", "landscape", "sunset"]}

        similarity = MaterialDeduplicator.calculate_similarity(metadata1, metadata2)

        assert similarity == 1.0

    def test_calculate_similarity_no_overlap(self):
        """测试相似度计算（无交集）"""
        metadata1 = {"tags": ["nature", "landscape"]}
        metadata2 = {"tags": ["city", "urban"]}

        similarity = MaterialDeduplicator.calculate_similarity(metadata1, metadata2)

        assert similarity == 0.0

    def test_calculate_similarity_partial_overlap(self):
        """测试相似度计算（部分交集）"""
        metadata1 = {"tags": ["nature", "landscape", "sunset"]}
        metadata2 = {"tags": ["nature", "landscape", "mountain"]}

        similarity = MaterialDeduplicator.calculate_similarity(metadata1, metadata2)

        # Jaccard: 2/4 = 0.5
        assert similarity == 0.5

    def test_find_similar_materials(self):
        """测试查找相似素材"""
        mock_db = Mock()
        target_material = Mock(spec=Material)
        target_material.id = 1
        target_material.material_type = "video"
        target_material.tags = ["nature", "landscape"]

        similar_material1 = Mock(spec=Material)
        similar_material1.id = 2
        similar_material1.material_type = "video"
        similar_material1.tags = ["nature", "landscape", "sunset"]

        similar_material2 = Mock(spec=Material)
        similar_material2.id = 3
        similar_material2.material_type = "video"
        similar_material2.tags = ["city", "urban"]

        mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = [
            similar_material1,
            similar_material2
        ]

        results = MaterialDeduplicator.find_similar_materials(
            mock_db,
            target_material,
            threshold=0.5
        )

        # Only similar_material1 should match
        assert len(results) == 1
        assert results[0][0] == similar_material1
