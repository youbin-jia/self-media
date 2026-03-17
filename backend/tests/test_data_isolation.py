# backend/tests/test_data_isolation.py
"""
Tests for data isolation with user_id foreign keys.

This test suite verifies that:
1. Material, Script, Task, and BatchJob models have user_id field
2. user_id is a foreign key to users.id
3. user_id is nullable for backward compatibility
4. user_id is indexed for query performance
5. Data isolation works correctly across different users
"""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.database import Base
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.material import Material
from app.models.script import Script
from app.models.task import Task
from app.models.batch import BatchJob


class TestMaterialDataIsolation:
    """Test data isolation for Material model"""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Setup test database"""
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        yield
        self.db.close()

    def test_material_has_user_id_field(self):
        """Test that Material model has user_id field"""
        inspector = inspect(Material)
        columns = {col.name: col for col in inspector.columns}
        assert 'user_id' in columns, "Material model should have user_id field"

    def test_material_user_id_is_nullable(self):
        """Test that Material.user_id is nullable for backward compatibility"""
        inspector = inspect(Material)
        user_id_col = inspector.columns.get('user_id')
        assert user_id_col is not None
        assert user_id_col.nullable is True, "user_id should be nullable for backward compatibility"

    def test_material_user_id_is_indexed(self):
        """Test that Material.user_id has an index for query performance"""
        table = Material.__table__
        user_id_indexes = [idx for idx in table.indexes if 'user_id' in idx.columns.keys()]
        assert len(user_id_indexes) > 0, "user_id should be indexed for query performance"

    def test_material_user_id_foreign_key_to_users(self):
        """Test that Material.user_id is a foreign key to users.id"""
        table = Material.__table__
        user_id_fk = [fk for fk in table.foreign_keys if fk.parent.name == 'user_id']
        assert len(user_id_fk) > 0, "user_id should be a foreign key"
        # Check it references users table
        fk = user_id_fk[0]
        assert fk.column.table.name == 'users', "user_id should reference users table"

    def test_material_can_be_created_with_user_id(self):
        """Test that Material can be created with user_id"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password"
        )
        self.db.add(user)
        self.db.commit()

        project = Project(
            title="Test Project",
            owner_id=user.id
        )
        self.db.add(project)
        self.db.commit()

        material = Material(
            project_id=project.id,
            user_id=user.id,
            material_type="video",
            source="local",
            local_path="/path/to/video.mp4",
            file_hash="abc123"
        )
        self.db.add(material)
        self.db.commit()

        assert material.user_id == user.id

    def test_material_can_be_created_without_user_id(self):
        """Test that Material can be created without user_id (backward compatibility)"""
        user = User(
            username="testuser2",
            email="test2@example.com",
            hashed_password="hashed_password"
        )
        self.db.add(user)
        self.db.commit()

        project = Project(
            title="Test Project 2",
            owner_id=user.id
        )
        self.db.add(project)
        self.db.commit()

        material = Material(
            project_id=project.id,
            material_type="video",
            source="local",
            local_path="/path/to/video2.mp4",
            file_hash="def456"
        )
        self.db.add(material)
        self.db.commit()

        assert material.user_id is None

    def test_material_data_isolation_by_user(self):
        """Test that materials can be queried by user_id for data isolation"""
        user1 = User(
            username="user1",
            email="user1@example.com",
            hashed_password="hashed1"
        )
        user2 = User(
            username="user2",
            email="user2@example.com",
            hashed_password="hashed2"
        )
        self.db.add_all([user1, user2])
        self.db.commit()

        project1 = Project(title="Project 1", owner_id=user1.id)
        project2 = Project(title="Project 2", owner_id=user2.id)
        self.db.add_all([project1, project2])
        self.db.commit()

        material1 = Material(
            project_id=project1.id,
            user_id=user1.id,
            material_type="video",
            source="local",
            local_path="/path/1.mp4",
            file_hash="hash1"
        )
        material2 = Material(
            project_id=project2.id,
            user_id=user2.id,
            material_type="video",
            source="local",
            local_path="/path/2.mp4",
            file_hash="hash2"
        )
        self.db.add_all([material1, material2])
        self.db.commit()

        # Query by user_id
        user1_materials = self.db.query(Material).filter(Material.user_id == user1.id).all()
        user2_materials = self.db.query(Material).filter(Material.user_id == user2.id).all()

        assert len(user1_materials) == 1
        assert len(user2_materials) == 1
        assert user1_materials[0].file_hash == "hash1"
        assert user2_materials[0].file_hash == "hash2"


class TestScriptDataIsolation:
    """Test data isolation for Script model"""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Setup test database"""
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        yield
        self.db.close()

    def test_script_has_user_id_field(self):
        """Test that Script model has user_id field"""
        inspector = inspect(Script)
        columns = {col.name: col for col in inspector.columns}
        assert 'user_id' in columns, "Script model should have user_id field"

    def test_script_user_id_is_nullable(self):
        """Test that Script.user_id is nullable for backward compatibility"""
        inspector = inspect(Script)
        user_id_col = inspector.columns.get('user_id')
        assert user_id_col is not None
        assert user_id_col.nullable is True, "user_id should be nullable for backward compatibility"

    def test_script_user_id_is_indexed(self):
        """Test that Script.user_id has an index for query performance"""
        table = Script.__table__
        user_id_indexes = [idx for idx in table.indexes if 'user_id' in idx.columns.keys()]
        assert len(user_id_indexes) > 0, "user_id should be indexed for query performance"

    def test_script_user_id_foreign_key_to_users(self):
        """Test that Script.user_id is a foreign key to users.id"""
        table = Script.__table__
        user_id_fk = [fk for fk in table.foreign_keys if fk.parent.name == 'user_id']
        assert len(user_id_fk) > 0, "user_id should be a foreign key"
        fk = user_id_fk[0]
        assert fk.column.table.name == 'users', "user_id should reference users table"

    def test_script_can_be_created_with_user_id(self):
        """Test that Script can be created with user_id"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password"
        )
        self.db.add(user)
        self.db.commit()

        project = Project(
            title="Test Project",
            owner_id=user.id
        )
        self.db.add(project)
        self.db.commit()

        script = Script(
            project_id=project.id,
            user_id=user.id,
            version=1,
            outline="Test outline"
        )
        self.db.add(script)
        self.db.commit()

        assert script.user_id == user.id

    def test_script_can_be_created_without_user_id(self):
        """Test that Script can be created without user_id (backward compatibility)"""
        user = User(
            username="testuser2",
            email="test2@example.com",
            hashed_password="hashed_password"
        )
        self.db.add(user)
        self.db.commit()

        project = Project(
            title="Test Project 2",
            owner_id=user.id
        )
        self.db.add(project)
        self.db.commit()

        script = Script(
            project_id=project.id,
            version=1,
            outline="Test outline"
        )
        self.db.add(script)
        self.db.commit()

        assert script.user_id is None


class TestTaskDataIsolation:
    """Test data isolation for Task model"""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Setup test database"""
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        yield
        self.db.close()

    def test_task_has_user_id_field(self):
        """Test that Task model has user_id field"""
        inspector = inspect(Task)
        columns = {col.name: col for col in inspector.columns}
        assert 'user_id' in columns, "Task model should have user_id field"

    def test_task_user_id_is_nullable(self):
        """Test that Task.user_id is nullable for backward compatibility"""
        inspector = inspect(Task)
        user_id_col = inspector.columns.get('user_id')
        assert user_id_col is not None
        assert user_id_col.nullable is True, "user_id should be nullable for backward compatibility"

    def test_task_user_id_is_indexed(self):
        """Test that Task.user_id has an index for query performance"""
        table = Task.__table__
        user_id_indexes = [idx for idx in table.indexes if 'user_id' in idx.columns.keys()]
        assert len(user_id_indexes) > 0, "user_id should be indexed for query performance"

    def test_task_user_id_foreign_key_to_users(self):
        """Test that Task.user_id is a foreign key to users.id"""
        table = Task.__table__
        user_id_fk = [fk for fk in table.foreign_keys if fk.parent.name == 'user_id']
        assert len(user_id_fk) > 0, "user_id should be a foreign key"
        fk = user_id_fk[0]
        assert fk.column.table.name == 'users', "user_id should reference users table"

    def test_task_can_be_created_with_user_id(self):
        """Test that Task can be created with user_id"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password"
        )
        self.db.add(user)
        self.db.commit()

        project = Project(
            title="Test Project",
            owner_id=user.id
        )
        self.db.add(project)
        self.db.commit()

        task = Task(
            project_id=project.id,
            user_id=user.id,
            task_type="video_generation",
            status="pending"
        )
        self.db.add(task)
        self.db.commit()

        assert task.user_id == user.id

    def test_task_can_be_created_without_user_id(self):
        """Test that Task can be created without user_id (backward compatibility)"""
        user = User(
            username="testuser2",
            email="test2@example.com",
            hashed_password="hashed_password"
        )
        self.db.add(user)
        self.db.commit()

        project = Project(
            title="Test Project 2",
            owner_id=user.id
        )
        self.db.add(project)
        self.db.commit()

        task = Task(
            project_id=project.id,
            task_type="video_generation",
            status="pending"
        )
        self.db.add(task)
        self.db.commit()

        assert task.user_id is None


class TestBatchJobDataIsolation:
    """Test data isolation for BatchJob model"""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Setup test database"""
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        yield
        self.db.close()

    def test_batch_job_has_user_id_field(self):
        """Test that BatchJob model has user_id field"""
        inspector = inspect(BatchJob)
        columns = {col.name: col for col in inspector.columns}
        assert 'user_id' in columns, "BatchJob model should have user_id field"

    def test_batch_job_user_id_is_nullable(self):
        """Test that BatchJob.user_id is nullable for backward compatibility"""
        inspector = inspect(BatchJob)
        user_id_col = inspector.columns.get('user_id')
        assert user_id_col is not None
        assert user_id_col.nullable is True, "user_id should be nullable for backward compatibility"

    def test_batch_job_user_id_is_indexed(self):
        """Test that BatchJob.user_id has an index for query performance"""
        table = BatchJob.__table__
        user_id_indexes = [idx for idx in table.indexes if 'user_id' in idx.columns.keys()]
        assert len(user_id_indexes) > 0, "user_id should be indexed for query performance"

    def test_batch_job_user_id_foreign_key_to_users(self):
        """Test that BatchJob.user_id is a foreign key to users.id"""
        table = BatchJob.__table__
        user_id_fk = [fk for fk in table.foreign_keys if fk.parent.name == 'user_id']
        assert len(user_id_fk) > 0, "user_id should be a foreign key"
        fk = user_id_fk[0]
        assert fk.column.table.name == 'users', "user_id should reference users table"

    def test_batch_job_can_be_created_with_user_id(self):
        """Test that BatchJob can be created with user_id"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password"
        )
        self.db.add(user)
        self.db.commit()

        batch = BatchJob(
            user_id=user.id,
            project_ids=["proj1", "proj2"],
            status="queued",
            total_projects=2
        )
        self.db.add(batch)
        self.db.commit()

        assert batch.user_id == user.id

    def test_batch_job_can_be_created_without_user_id(self):
        """Test that BatchJob can be created without user_id (backward compatibility)"""
        batch = BatchJob(
            project_ids=["proj1", "proj2"],
            status="queued",
            total_projects=2
        )
        self.db.add(batch)
        self.db.commit()

        assert batch.user_id is None

    def test_batch_job_data_isolation_by_user(self):
        """Test that batch jobs can be queried by user_id for data isolation"""
        user1 = User(
            username="user1",
            email="user1@example.com",
            hashed_password="hashed1"
        )
        user2 = User(
            username="user2",
            email="user2@example.com",
            hashed_password="hashed2"
        )
        self.db.add_all([user1, user2])
        self.db.commit()

        batch1 = BatchJob(
            user_id=user1.id,
            project_ids=["proj1"],
            status="completed",
            total_projects=1
        )
        batch2 = BatchJob(
            user_id=user2.id,
            project_ids=["proj2"],
            status="running",
            total_projects=1
        )
        self.db.add_all([batch1, batch2])
        self.db.commit()

        # Query by user_id
        user1_batches = self.db.query(BatchJob).filter(BatchJob.user_id == user1.id).all()
        user2_batches = self.db.query(BatchJob).filter(BatchJob.user_id == user2.id).all()

        assert len(user1_batches) == 1
        assert len(user2_batches) == 1
        assert user1_batches[0].status == "completed"
        assert user2_batches[0].status == "running"


class TestComprehensiveDataIsolation:
    """Comprehensive tests for data isolation across all models"""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Setup test database"""
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        yield
        self.db.close()

    def test_all_models_have_user_id(self):
        """Test that all required models have user_id field"""
        models_to_check = [Material, Script, Task, BatchJob]

        for model in models_to_check:
            inspector = inspect(model)
            columns = {col.name: col for col in inspector.columns}
            assert 'user_id' in columns, f"{model.__name__} should have user_id field"

    def test_all_user_ids_are_nullable(self):
        """Test that all user_id fields are nullable for backward compatibility"""
        models_to_check = [Material, Script, Task, BatchJob]

        for model in models_to_check:
            inspector = inspect(model)
            user_id_col = inspector.columns.get('user_id')
            assert user_id_col is not None
            assert user_id_col.nullable is True, \
                f"{model.__name__}.user_id should be nullable for backward compatibility"

    def test_all_user_ids_are_indexed(self):
        """Test that all user_id fields are indexed for query performance"""
        models_to_check = [Material, Script, Task, BatchJob]

        for model in models_to_check:
            table = model.__table__
            user_id_indexes = [idx for idx in table.indexes if 'user_id' in idx.columns.keys()]
            assert len(user_id_indexes) > 0, \
                f"{model.__name__}.user_id should be indexed for query performance"

    def test_all_user_ids_reference_users_table(self):
        """Test that all user_id fields are foreign keys to users.id"""
        models_to_check = [Material, Script, Task, BatchJob]

        for model in models_to_check:
            table = model.__table__
            user_id_fk = [fk for fk in table.foreign_keys if fk.parent.name == 'user_id']
            assert len(user_id_fk) > 0, \
                f"{model.__name__}.user_id should be a foreign key"
            fk = user_id_fk[0]
            assert fk.column.table.name == 'users', \
                f"{model.__name__}.user_id should reference users table"

    def test_cross_model_data_isolation(self):
        """Test that data isolation works across all models for a user"""
        # Create users
        user1 = User(
            username="user1",
            email="user1@example.com",
            hashed_password="hashed1"
        )
        user2 = User(
            username="user2",
            email="user2@example.com",
            hashed_password="hashed2"
        )
        self.db.add_all([user1, user2])
        self.db.commit()

        # Create projects
        project1 = Project(title="Project 1", owner_id=user1.id)
        project2 = Project(title="Project 2", owner_id=user2.id)
        self.db.add_all([project1, project2])
        self.db.commit()

        # Create materials
        material1 = Material(
            project_id=project1.id,
            user_id=user1.id,
            material_type="video",
            source="local",
            local_path="/path/1.mp4",
            file_hash="hash1"
        )
        material2 = Material(
            project_id=project2.id,
            user_id=user2.id,
            material_type="video",
            source="local",
            local_path="/path/2.mp4",
            file_hash="hash2"
        )
        self.db.add_all([material1, material2])

        # Create scripts
        script1 = Script(
            project_id=project1.id,
            user_id=user1.id,
            version=1,
            outline="Script 1"
        )
        script2 = Script(
            project_id=project2.id,
            user_id=user2.id,
            version=1,
            outline="Script 2"
        )
        self.db.add_all([script1, script2])

        # Create tasks
        task1 = Task(
            project_id=project1.id,
            user_id=user1.id,
            task_type="generation",
            status="completed"
        )
        task2 = Task(
            project_id=project2.id,
            user_id=user2.id,
            task_type="generation",
            status="pending"
        )
        self.db.add_all([task1, task2])

        # Create batch jobs
        batch1 = BatchJob(
            user_id=user1.id,
            project_ids=[project1.id],
            status="completed",
            total_projects=1
        )
        batch2 = BatchJob(
            user_id=user2.id,
            project_ids=[project2.id],
            status="queued",
            total_projects=1
        )
        self.db.add_all([batch1, batch2])
        self.db.commit()

        # Query all data for user1
        user1_materials = self.db.query(Material).filter(Material.user_id == user1.id).all()
        user1_scripts = self.db.query(Script).filter(Script.user_id == user1.id).all()
        user1_tasks = self.db.query(Task).filter(Task.user_id == user1.id).all()
        user1_batches = self.db.query(BatchJob).filter(BatchJob.user_id == user1.id).all()

        # Query all data for user2
        user2_materials = self.db.query(Material).filter(Material.user_id == user2.id).all()
        user2_scripts = self.db.query(Script).filter(Script.user_id == user2.id).all()
        user2_tasks = self.db.query(Task).filter(Task.user_id == user2.id).all()
        user2_batches = self.db.query(BatchJob).filter(BatchJob.user_id == user2.id).all()

        # Verify user1 data
        assert len(user1_materials) == 1
        assert len(user1_scripts) == 1
        assert len(user1_tasks) == 1
        assert len(user1_batches) == 1
        assert user1_materials[0].file_hash == "hash1"
        assert user1_scripts[0].outline == "Script 1"
        assert user1_tasks[0].status == "completed"
        assert user1_batches[0].status == "completed"

        # Verify user2 data
        assert len(user2_materials) == 1
        assert len(user2_scripts) == 1
        assert len(user2_tasks) == 1
        assert len(user2_batches) == 1
        assert user2_materials[0].file_hash == "hash2"
        assert user2_scripts[0].outline == "Script 2"
        assert user2_tasks[0].status == "pending"
        assert user2_batches[0].status == "queued"
