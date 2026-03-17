# backend/tests/test_auth.py
"""Tests for User model and authentication"""
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.database import Base
from app.models.user import User, UserRole
from app.models.project import Project
from app.services.auth.jwt_handler import JWTHandler
from app.config import settings
import jwt
import time


class TestUserModel:
    """Test cases for User model"""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Setup test database"""
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        Base.metadata.create_all(bind=engine)

        self.db = SessionLocal()
        yield
        self.db.close()

    def test_create_user(self):
        """Test creating a basic user"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123",
            role=UserRole.VIEWER
        )
        self.db.add(user)
        self.db.commit()

        assert user.id is not None
        assert len(user.id) == 36  # UUID format
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_123"
        assert user.role == UserRole.VIEWER
        assert user.is_active is True
        assert user.created_at is not None

    def test_user_default_role_is_viewer(self):
        """Test that default role is viewer"""
        user = User(
            username="testuser2",
            email="test2@example.com",
            hashed_password="hashed_password_456"
        )
        self.db.add(user)
        self.db.commit()

        assert user.role == UserRole.VIEWER

    def test_user_unique_username(self):
        """Test that username must be unique"""
        user1 = User(
            username="duplicate",
            email="user1@example.com",
            hashed_password="password1"
        )
        user2 = User(
            username="duplicate",
            email="user2@example.com",
            hashed_password="password2"
        )

        self.db.add(user1)
        self.db.commit()

        self.db.add(user2)
        with pytest.raises(IntegrityError):
            self.db.commit()

    def test_user_unique_email(self):
        """Test that email must be unique"""
        user1 = User(
            username="user1",
            email="duplicate@example.com",
            hashed_password="password1"
        )
        user2 = User(
            username="user2",
            email="duplicate@example.com",
            hashed_password="password2"
        )

        self.db.add(user1)
        self.db.commit()

        self.db.add(user2)
        with pytest.raises(IntegrityError):
            self.db.commit()

    def test_user_roles(self):
        """Test all user roles"""
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password="admin_pass",
            role=UserRole.ADMIN
        )
        editor = User(
            username="editor",
            email="editor@example.com",
            hashed_password="editor_pass",
            role=UserRole.EDITOR
        )
        viewer = User(
            username="viewer",
            email="viewer@example.com",
            hashed_password="viewer_pass",
            role=UserRole.VIEWER
        )

        self.db.add_all([admin, editor, viewer])
        self.db.commit()

        assert admin.role == UserRole.ADMIN
        assert editor.role == UserRole.EDITOR
        assert viewer.role == UserRole.VIEWER

    def test_user_role_string_values(self):
        """Test UserRole enum string values"""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.EDITOR.value == "editor"
        assert UserRole.VIEWER.value == "viewer"

    def test_user_is_active_default(self):
        """Test that is_active defaults to True"""
        user = User(
            username="active_user",
            email="active@example.com",
            hashed_password="password"
        )
        self.db.add(user)
        self.db.commit()

        assert user.is_active is True

    def test_user_is_active_can_be_false(self):
        """Test that is_active can be set to False"""
        user = User(
            username="inactive_user",
            email="inactive@example.com",
            hashed_password="password",
            is_active=False
        )
        self.db.add(user)
        self.db.commit()

        assert user.is_active is False

    def test_user_timestamps(self):
        """Test that created_at and updated_at work correctly"""
        user = User(
            username="timestamp_user",
            email="timestamp@example.com",
            hashed_password="password"
        )
        self.db.add(user)
        self.db.commit()

        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)

        # Update user
        user.username = "updated_user"
        self.db.commit()

        # updated_at should be set after update
        assert user.updated_at is not None
        assert isinstance(user.updated_at, datetime)

    def test_user_repr(self):
        """Test user string representation"""
        user = User(
            username="repr_user",
            email="repr@example.com",
            hashed_password="password",
            role=UserRole.EDITOR
        )
        self.db.add(user)
        self.db.commit()

        repr_str = repr(user)
        assert "User" in repr_str
        assert user.username in repr_str
        assert user.email in repr_str
        # role is stored as string in DB, so user.role is "editor" not UserRole.EDITOR
        assert user.role in repr_str

    def test_user_project_relationship(self):
        """Test that User-Project relationship works correctly"""
        # Create a user
        user = User(
            username="project_owner",
            email="owner@example.com",
            hashed_password="password",
            role=UserRole.EDITOR
        )
        self.db.add(user)
        self.db.commit()

        # Create projects owned by the user
        project1 = Project(
            title="Project 1",
            status="pending",
            owner_id=user.id
        )
        project2 = Project(
            title="Project 2",
            status="active",
            owner_id=user.id
        )
        self.db.add_all([project1, project2])
        self.db.commit()

        # Refresh to load relationships
        self.db.refresh(user)
        self.db.refresh(project1)
        self.db.refresh(project2)

        # Verify user has projects relationship
        assert hasattr(user, 'projects')
        assert len(user.projects) == 2
        assert project1 in user.projects
        assert project2 in user.projects

        # Verify projects have owner relationship
        assert hasattr(project1, 'owner')
        assert project1.owner == user
        assert project1.owner_id == user.id
        assert project2.owner == user
        assert project2.owner_id == user.id

    def test_project_can_have_null_owner(self):
        """Test that project owner_id can be null"""
        project = Project(
            title="Orphan Project",
            status="pending"
        )
        self.db.add(project)
        self.db.commit()

        assert project.id is not None
        assert project.owner_id is None
        assert project.owner is None

    def test_user_can_have_no_projects(self):
        """Test that a user can exist without projects"""
        user = User(
            username="user_no_projects",
            email="no_projects@example.com",
            hashed_password="password"
        )
        self.db.add(user)
        self.db.commit()

        self.db.refresh(user)
        assert hasattr(user, 'projects')
        assert len(user.projects) == 0

    def test_user_null_username_violation(self):
        """Test that username cannot be null"""
        user = User(
            username=None,
            email="null_username@example.com",
            hashed_password="password"
        )
        self.db.add(user)
        with pytest.raises(IntegrityError):
            self.db.commit()

    def test_user_null_email_violation(self):
        """Test that email cannot be null"""
        user = User(
            username="null_email_user",
            email=None,
            hashed_password="password"
        )
        self.db.add(user)
        with pytest.raises(IntegrityError):
            self.db.commit()

    def test_user_null_password_violation(self):
        """Test that hashed_password cannot be null"""
        user = User(
            username="null_password_user",
            email="null_password@example.com",
            hashed_password=None
        )
        self.db.add(user)
        with pytest.raises(IntegrityError):
            self.db.commit()

    def test_user_invalid_role_validation(self):
        """Test that invalid role values are rejected by check constraint"""
        user = User(
            username="invalid_role_user",
            email="invalid_role@example.com",
            hashed_password="password",
            role="invalid_role"
        )
        self.db.add(user)
        with pytest.raises(IntegrityError):
            self.db.commit()


class TestJWTHandler:
    """Test cases for JWT Handler"""

    @pytest.fixture
    def jwt_handler(self):
        """Create a JWTHandler instance for testing"""
        return JWTHandler()

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for token creation"""
        return {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "username": "testuser",
            "role": "editor"
        }

    def test_create_access_token(self, jwt_handler, sample_user_data):
        """Test creating an access token"""
        token = jwt_handler.create_access_token(
            user_id=sample_user_data["user_id"],
            username=sample_user_data["username"],
            role=sample_user_data["role"]
        )

        assert token is not None
        assert isinstance(token, str)
        # Verify it's a valid JWT (3 parts separated by dots)
        assert token.count('.') == 2

    def test_decode_valid_token(self, jwt_handler, sample_user_data):
        """Test decoding a valid token"""
        token = jwt_handler.create_access_token(
            user_id=sample_user_data["user_id"],
            username=sample_user_data["username"],
            role=sample_user_data["role"]
        )

        payload = jwt_handler.decode_token(token)

        assert payload is not None
        assert payload["user_id"] == sample_user_data["user_id"]
        assert payload["username"] == sample_user_data["username"]
        assert payload["role"] == sample_user_data["role"]
        assert "exp" in payload
        assert "iat" in payload

    def test_token_expiration_time(self, jwt_handler, sample_user_data):
        """Test that token has correct expiration time (7 days by default)"""
        token = jwt_handler.create_access_token(
            user_id=sample_user_data["user_id"],
            username=sample_user_data["username"],
            role=sample_user_data["role"]
        )

        payload = jwt_handler.decode_token(token)

        # Check expiration is approximately 7 days from now
        exp = datetime.fromtimestamp(payload["exp"])
        iat = datetime.fromtimestamp(payload["iat"])

        # Should be approximately 7 days (168 hours) difference
        delta = exp - iat
        expected_delta = timedelta(hours=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS)

        # Allow 1 second tolerance
        assert abs(delta.total_seconds() - expected_delta.total_seconds()) < 1

    def test_expired_token_returns_none(self, jwt_handler, sample_user_data):
        """Test that expired tokens return None when decoded"""
        # Create an already expired token by using negative expiration
        expired_token = jwt.encode(
            {
                "user_id": sample_user_data["user_id"],
                "username": sample_user_data["username"],
                "role": sample_user_data["role"],
                "exp": datetime.utcnow() - timedelta(hours=1),
                "iat": datetime.utcnow() - timedelta(hours=2)
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        payload = jwt_handler.decode_token(expired_token)
        assert payload is None

    def test_invalid_token_returns_none(self, jwt_handler):
        """Test that invalid tokens return None when decoded"""
        # Completely invalid token string
        invalid_token = "invalid.token.string"

        payload = jwt_handler.decode_token(invalid_token)
        assert payload is None

    def test_token_with_wrong_secret_returns_none(self, jwt_handler, sample_user_data):
        """Test that token signed with wrong secret returns None"""
        wrong_secret_token = jwt.encode(
            {
                "user_id": sample_user_data["user_id"],
                "username": sample_user_data["username"],
                "role": sample_user_data["role"],
                "exp": datetime.utcnow() + timedelta(days=7),
                "iat": datetime.utcnow()
            },
            "wrong-secret-key",
            algorithm=settings.JWT_ALGORITHM
        )

        payload = jwt_handler.decode_token(wrong_secret_token)
        assert payload is None

    def test_token_with_missing_claims_returns_payload(self, jwt_handler):
        """Test that token with missing required claims still returns payload"""
        # Token missing 'role' claim
        token_without_role = jwt.encode(
            {
                "user_id": "some-user-id",
                "username": "someuser",
                "exp": datetime.utcnow() + timedelta(days=7),
                "iat": datetime.utcnow()
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        # decode_token should still return the payload (validation happens elsewhere)
        payload = jwt_handler.decode_token(token_without_role)
        assert payload is not None
        assert payload["user_id"] == "some-user-id"

    def test_create_token_with_custom_expiration(self, jwt_handler, sample_user_data):
        """Test creating token with custom expiration time"""
        custom_expire_hours = 24

        token = jwt_handler.create_access_token(
            user_id=sample_user_data["user_id"],
            username=sample_user_data["username"],
            role=sample_user_data["role"],
            expires_delta=timedelta(hours=custom_expire_hours)
        )

        payload = jwt_handler.decode_token(token)

        exp = datetime.fromtimestamp(payload["exp"])
        iat = datetime.fromtimestamp(payload["iat"])
        delta = exp - iat

        expected_delta = timedelta(hours=custom_expire_hours)
        assert abs(delta.total_seconds() - expected_delta.total_seconds()) < 1

    def test_all_roles_in_token(self, jwt_handler):
        """Test that all valid roles can be encoded in token"""
        roles = ["admin", "editor", "viewer"]

        for role in roles:
            token = jwt_handler.create_access_token(
                user_id=f"user-{role}",
                username=f"user_{role}",
                role=role
            )
            payload = jwt_handler.decode_token(token)
            assert payload["role"] == role

    def test_token_contains_issued_at(self, jwt_handler, sample_user_data):
        """Test that token contains issued at (iat) timestamp"""
        before_create = datetime.now(timezone.utc)
        token = jwt_handler.create_access_token(
            user_id=sample_user_data["user_id"],
            username=sample_user_data["username"],
            role=sample_user_data["role"]
        )
        after_create = datetime.now(timezone.utc)

        payload = jwt_handler.decode_token(token)

        assert "iat" in payload
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

        # JWT iat has second precision, so we need to account for truncation
        # Check that iat is within a reasonable range (within 1 second)
        assert abs((iat - before_create).total_seconds()) < 1
        assert abs((after_create - iat).total_seconds()) < 2
