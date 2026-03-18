# backend/tests/conftest.py
"""Pytest configuration and fixtures"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import uuid

# Import all models first to register them with Base
from app.models import user, project, script, material, task, batch, quality_report, plugin, webhook  # noqa: F401

from app.database import Base, get_db


# Test database setup with StaticPool for thread-safe single-connection testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Global variable for current test session
_current_test_session = None


def override_get_db():
    """Override database dependency for testing"""
    global _current_test_session
    if _current_test_session is not None:
        yield _current_test_session
    else:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Set up test database for the entire test session"""
    from app.main import app

    # Override the database dependency at module level
    app.dependency_overrides[get_db] = override_get_db

    # Disable startup event that creates tables
    app.router.on_startup = []

    # Create tables
    Base.metadata.create_all(bind=engine)

    yield

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_db() -> Session:
    """Create a database session for testing with isolation"""
    global _current_test_session

    # Start a connection and transaction for this test
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    # Set global session for override_get_db
    _current_test_session = session

    yield session

    # Cleanup
    _current_test_session = None
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client() -> TestClient:
    """Create test client with test database"""
    from app.main import app

    # Ensure dependency override is set
    if get_db not in app.dependency_overrides:
        app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_user(test_db: Session):
    """Create an admin user for testing"""
    from passlib.context import CryptContext
    from app.models.user import User, UserRole

    # Use unique username to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    admin = User(
        username=f"admin_{unique_id}",
        email=f"admin_{unique_id}@example.com",
        hashed_password=pwd_context.hash("AdminPassword123!"),
        role=UserRole.ADMIN.value
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin


@pytest.fixture
def editor_user(test_db: Session):
    """Create an editor user for testing"""
    from passlib.context import CryptContext
    from app.models.user import User, UserRole

    # Use unique username to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    editor = User(
        username=f"editor_{unique_id}",
        email=f"editor_{unique_id}@example.com",
        hashed_password=pwd_context.hash("EditorPassword123!"),
        role=UserRole.EDITOR.value
    )
    test_db.add(editor)
    test_db.commit()
    test_db.refresh(editor)
    return editor


@pytest.fixture
def viewer_user(test_db: Session):
    """Create a viewer user for testing"""
    from passlib.context import CryptContext
    from app.models.user import User, UserRole

    # Use unique username to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    viewer = User(
        username=f"viewer_{unique_id}",
        email=f"viewer_{unique_id}@example.com",
        hashed_password=pwd_context.hash("ViewerPassword123!"),
        role=UserRole.VIEWER.value
    )
    test_db.add(viewer)
    test_db.commit()
    test_db.refresh(viewer)
    return viewer


@pytest.fixture
def admin_token(client: TestClient, admin_user):
    """Get admin access token"""
    response = client.post("/api/auth/login", json={
        "username": admin_user.username,
        "password": "AdminPassword123!"
    })
    return response.json()["access_token"]


@pytest.fixture
def editor_token(client: TestClient, editor_user):
    """Get editor access token"""
    response = client.post("/api/auth/login", json={
        "username": editor_user.username,
        "password": "EditorPassword123!"
    })
    return response.json()["access_token"]


@pytest.fixture
def viewer_token(client: TestClient, viewer_user):
    """Get viewer access token"""
    response = client.post("/api/auth/login", json={
        "username": viewer_user.username,
        "password": "ViewerPassword123!"
    })
    return response.json()["access_token"]
