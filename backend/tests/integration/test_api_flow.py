# backend/tests/integration/test_api_flow.py
"""End-to-end API flow tests for video production workflow"""
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import Base, get_db
from app.main import app


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    """Create test client with test database"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for video synthesis"""
    with patch("app.api.video.synthesize_video_task") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "test-task-id-123"
        mock_task.delay.return_value = mock_result
        yield mock_task


@pytest.fixture
def mock_celery_app():
    """Mock Celery app for task status checks"""
    with patch("app.api.video.celery_app") as mock_app:
        mock_async_result = MagicMock()
        mock_async_result.status = "SUCCESS"
        mock_async_result.result = {"output_path": "/output/video.mp4"}
        mock_app.AsyncResult.return_value = mock_async_result
        yield mock_app


class TestEndToEndFlow:
    """End-to-end tests for complete video production workflow"""

    def test_01_get_topics_list(self, client):
        """Step 1: Get topics list from monitored platforms"""
        response = client.get("/api/topics/list")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "count" in data
        assert isinstance(data["data"], list)

    def test_02_create_project(self, client):
        """Step 2: Create a new project"""
        project_data = {
            "title": "Test Video Project",
            "topic_source": "weibo",
            "topic_title": "AI Technology Trends 2024",
            "topic_hot_score": 9500000,
            "metadata": {
                "description": "A video about AI trends"
            }
        }

        response = client.post("/api/projects/", json=project_data)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == project_data["title"]
        assert data["topic_source"] == project_data["topic_source"]
        assert data["topic_title"] == project_data["topic_title"]
        assert data["topic_hot_score"] == project_data["topic_hot_score"]
        assert data["status"] == "pending"
        assert "id" in data

        # Store project_id for subsequent tests
        self.__class__.project_id = data["id"]

    def test_03_generate_script_outline(self, client):
        """Step 3: Generate script outline for the project"""
        project_id = getattr(self.__class__, "project_id", None)
        assert project_id is not None, "Project ID not found. Run create_project first."

        with patch("app.api.scripts.ScriptGenerator") as MockGenerator:
            mock_generator = MagicMock()
            mock_generator.generate_outline = AsyncMock(return_value="Outline text here...")
            MockGenerator.return_value = mock_generator

            response = client.post(
                "/api/scripts/generate-outline",
                params={"project_id": project_id}
            )

        assert response.status_code == 200
        data = response.json()
        assert "script_id" in data
        assert "outline" in data

        # Store script_id for subsequent tests
        self.__class__.script_id = data["script_id"]

    def test_04_generate_full_script(self, client):
        """Step 4: Generate full script with segments"""
        project_id = getattr(self.__class__, "project_id", None)
        assert project_id is not None

        mock_segments = [
            {
                "segment_id": 1,
                "type": "opening",
                "duration": 5.0,
                "narration": "Welcome to our video",
                "visual_description": "Title screen"
            },
            {
                "segment_id": 2,
                "type": "main_content",
                "duration": 30.0,
                "narration": "Let's explore AI trends",
                "visual_description": "AI visualization"
            }
        ]

        with patch("app.api.scripts.ScriptGenerator") as MockGenerator:
            mock_generator = MagicMock()
            mock_generator.generate_full_script = AsyncMock(return_value={
                "full_script": "Full script text...",
                "segments": mock_segments
            })
            MockGenerator.return_value = mock_generator

            response = client.post(
                "/api/scripts/generate-full",
                params={"project_id": project_id}
            )

        assert response.status_code == 200
        data = response.json()
        assert "full_script" in data
        assert "segments" in data

    def test_05_approve_script(self, client):
        """Step 5: Approve the script"""
        script_id = getattr(self.__class__, "script_id", None)
        assert script_id is not None

        response = client.post(f"/api/scripts/{script_id}/approve")

        assert response.status_code == 200
        data = response.json()
        assert data["is_approved"] is True

    def test_06_collect_materials(self, client):
        """Step 6: Collect materials for the project"""
        project_id = getattr(self.__class__, "project_id", None)
        assert project_id is not None

        mock_images = [
            {
                "id": "img-1",
                "type": "image",
                "source": "pexels",
                "source_url": "https://example.com/image1.jpg",
                "thumbnail_url": "https://example.com/thumb1.jpg",
                "width": 1920,
                "height": 1080,
                "photographer": "Test Photographer"
            },
            {
                "id": "img-2",
                "type": "image",
                "source": "pexels",
                "source_url": "https://example.com/image2.jpg",
                "thumbnail_url": "https://example.com/thumb2.jpg",
                "width": 1920,
                "height": 1080,
                "photographer": "Another Photographer"
            }
        ]

        with patch("app.api.materials.MaterialCollector") as MockCollector:
            mock_collector = MagicMock()
            mock_collector.extract_keywords.return_value = ["AI", "technology", "2024"]
            mock_collector.search_images = AsyncMock(return_value=mock_images)
            MockCollector.return_value = mock_collector

            response = client.post(
                "/api/materials/collect",
                params={"project_id": project_id}
            )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_07_trigger_video_synthesis(self, client, mock_celery_task):
        """Step 7: Trigger video synthesis"""
        project_id = getattr(self.__class__, "project_id", None)
        assert project_id is not None

        # First update project metadata with materials
        # (materials were collected in previous step, but we need to update the project)
        response = client.put(
            f"/api/projects/{project_id}",
            json={"metadata": {"materials": ["img-1", "img-2"]}}
        )
        assert response.status_code == 200

        response = client.post(
            "/api/video/synthesize",
            json={"project_id": project_id}
        )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["project_id"] == project_id

        # Store task_id for status check
        self.__class__.task_id = data["task_id"]

    def test_08_check_task_status(self, client, mock_celery_app):
        """Step 8: Check video synthesis task status"""
        task_id = getattr(self.__class__, "task_id", "test-task-id-123")

        response = client.get(f"/api/video/status/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "status" in data
        assert "progress" in data
        assert "message" in data

    def test_complete_flow(self, client, mock_celery_task, mock_celery_app):
        """Complete end-to-end flow test combining all steps"""
        # Step 1: Get topics
        response = client.get("/api/topics/list")
        assert response.status_code == 200
        topics_data = response.json()

        # Step 2: Create project
        project_data = {
            "title": "Complete Flow Test Project",
            "topic_source": "douyin",
            "topic_title": "Complete E2E Test",
            "topic_hot_score": 5000000
        }
        response = client.post("/api/projects/", json=project_data)
        assert response.status_code == 201
        project = response.json()
        project_id = project["id"]

        # Step 3: Generate outline
        with patch("app.api.scripts.ScriptGenerator") as MockGenerator:
            mock_generator = MagicMock()
            mock_generator.generate_outline = AsyncMock(return_value="Test outline")
            MockGenerator.return_value = mock_generator

            response = client.post(
                "/api/scripts/generate-outline",
                params={"project_id": project_id}
            )
        assert response.status_code == 200
        script_id = response.json()["script_id"]

        # Step 4: Generate full script
        with patch("app.api.scripts.ScriptGenerator") as MockGenerator:
            mock_generator = MagicMock()
            mock_generator.generate_full_script = AsyncMock(return_value={
                "full_script": "Full script",
                "segments": [{"segment_id": 1, "type": "main", "duration": 10.0}]
            })
            MockGenerator.return_value = mock_generator

            response = client.post(
                "/api/scripts/generate-full",
                params={"project_id": project_id}
            )
        assert response.status_code == 200

        # Step 5: Approve script
        response = client.post(f"/api/scripts/{script_id}/approve")
        assert response.status_code == 200

        # Step 6: Collect materials
        with patch("app.api.materials.MaterialCollector") as MockCollector:
            mock_collector = MagicMock()
            mock_collector.extract_keywords.return_value = ["test"]
            mock_collector.search_images = AsyncMock(return_value=[{
                "id": "img-e2e",
                "type": "image",
                "source": "test",
                "source_url": "https://test.com/img.jpg"
            }])
            MockCollector.return_value = mock_collector

            response = client.post(
                "/api/materials/collect",
                params={"project_id": project_id}
            )
        assert response.status_code == 200

        # Update project with materials
        client.put(
            f"/api/projects/{project_id}",
            json={"metadata": {"materials": ["img-e2e"]}}
        )

        # Step 7: Trigger synthesis
        response = client.post(
            "/api/video/synthesize",
            json={"project_id": project_id}
        )
        assert response.status_code == 202
        task_id = response.json()["task_id"]

        # Step 8: Check status
        response = client.get(f"/api/video/status/{task_id}")
        assert response.status_code == 200

        # Final assertion
        assert True, "Complete flow test passed"


class TestHealthEndpoints:
    """Tests for health and root endpoints"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns expected data"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Video Automation API"
        assert data["status"] == "running"

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestProjectEndpoints:
    """Tests for project API endpoints"""

    def test_list_projects(self, client):
        """Test listing projects"""
        response = client.get("/api/projects/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_projects_with_status_filter(self, client):
        """Test listing projects with status filter"""
        response = client.get("/api/projects/?status=pending")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_nonexistent_project(self, client):
        """Test getting a non-existent project returns 404"""
        response = client.get("/api/projects/nonexistent-id")

        assert response.status_code == 404

    def test_delete_nonexistent_project(self, client):
        """Test deleting a non-existent project returns 404"""
        response = client.delete("/api/projects/nonexistent-id")

        assert response.status_code == 404
