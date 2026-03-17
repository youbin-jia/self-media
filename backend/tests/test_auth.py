# backend/tests/test_auth.py
"""Tests for User model and authentication"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.database import Base
from app.models.user import User, UserRole
from app.models.project import Project


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
