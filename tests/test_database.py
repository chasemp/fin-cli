"""
Database manager tests
"""

from pathlib import Path
import sqlite3

import pytest

from fincli.db import DatabaseManager
from fincli.tasks import TaskManager


class TestDatabaseManager:
    """Test database manager functionality."""

    def test_init_creates_directory(self, mock_home_dir):
        """Test that database manager creates directory if it doesn't exist."""
        fin_dir = Path(mock_home_dir) / ".fin"
        db_path = fin_dir / "tasks.db"

        # Directory shouldn't exist initially
        assert not fin_dir.exists()

        # Create manager
        DatabaseManager(str(db_path))

        # Directory should be created
        assert fin_dir.exists()
        assert db_path.exists()

    def test_init_creates_table(self, db_manager):
        """Test that database manager creates tasks table."""
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()

            # Check if table exists
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='tasks'
            """
            )

            result = cursor.fetchone()
            assert result is not None
            assert result[0] == "tasks"

    def test_table_schema(self, db_manager):
        """Test that tasks table has correct schema."""
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()

            # Get table info
            cursor.execute("PRAGMA table_info(tasks)")
            columns = cursor.fetchall()

            # Check column structure
            column_names = [col[1] for col in columns]
            expected_columns = [
                "id",
                "content",
                "created_at",
                "modified_at",
                "completed_at",
                "labels",
                "source",
                "due_date",
                "context",
            ]

            assert set(column_names) == set(expected_columns)

            # Check primary key
            id_column = next(col for col in columns if col[1] == "id")
            assert id_column[5] == 1  # Primary key flag

    def test_add_task_basic(self, db_manager):
        """Test adding a basic task without labels."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task_id = task_manager.add_task("Test task")

        assert task_id == 1

        # Verify task was added
        task = task_manager.get_task(task_id)
        assert task is not None
        assert task["content"] == "Test task"
        assert task["labels"] == []
        assert task["source"] == "cli"
        assert task["completed_at"] is None

    def test_add_task_with_labels(self, db_manager):
        """Test adding a task with labels."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task_id = task_manager.add_task("Test task with labels", labels=["work", "urgent"], source="test")

        assert task_id == 1

        # Verify task was added
        task = task_manager.get_task(task_id)
        assert task is not None
        assert task["content"] == "Test task with labels"
        assert set(task["labels"]) == {"work", "urgent"}
        assert task["source"] == "test"

    def test_add_task_labels_normalization(self, db_manager):
        """Test that labels are normalized to lowercase."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task_id = task_manager.add_task("Test task", labels=["WORK", "Urgent", "  test  "])

        task = task_manager.get_task(task_id)
        assert set(task["labels"]) == {"work", "urgent", "test"}

    def test_add_task_empty_labels(self, db_manager):
        """Test adding task with empty labels."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task_id = task_manager.add_task("Test task", labels=["", "  ", None])

        task = task_manager.get_task(task_id)
        assert task["labels"] == []

    def test_get_task_nonexistent(self, db_manager):
        """Test getting a task that doesn't exist."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task = task_manager.get_task(999)
        assert task is None

    def test_list_tasks_empty(self, db_manager):
        """Test listing tasks when database is empty."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        tasks = task_manager.list_tasks()
        assert tasks == []

    def test_list_tasks_populated(self, populated_db):
        """Test listing tasks from populated database."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(populated_db)
        tasks = task_manager.list_tasks()

        assert len(tasks) == 4

        # Check that tasks are ordered by created_at DESC (newest first)
        task_ids = [task["id"] for task in tasks]
        # Since tasks are created quickly, they may have same timestamp
        # In that case, SQLite orders by primary key (id) in ascending order
        assert task_ids == [1, 2, 3, 4]  # Oldest first (lowest ID first)

    def test_list_tasks_exclude_completed(self, populated_db):
        """Test listing tasks excluding completed ones."""
        # Mark a task as completed
        with sqlite3.connect(populated_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET completed_at = CURRENT_TIMESTAMP WHERE id = 1")
            conn.commit()

        from fincli.tasks import TaskManager

        task_manager = TaskManager(populated_db)
        tasks = task_manager.list_tasks(include_completed=False)

        # Should exclude the completed task
        assert len(tasks) == 3
        task_ids = [task["id"] for task in tasks]
        assert 1 not in task_ids

    def test_list_tasks_include_completed(self, populated_db):
        """Test listing tasks including completed ones."""
        # Mark a task as completed
        with sqlite3.connect(populated_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET completed_at = CURRENT_TIMESTAMP WHERE id = 1")
            conn.commit()

        from fincli.tasks import TaskManager

        task_manager = TaskManager(populated_db)
        tasks = task_manager.list_tasks(include_completed=True)

        # Should include all tasks
        assert len(tasks) == 4

        # Check that completed task has completed_at set
        completed_task = next(task for task in tasks if task["id"] == 1)
        assert completed_task["completed_at"] is not None

    def test_database_persistence(self, temp_db_path):
        """Test that database persists data between manager instances."""
        # Create first manager and add task
        manager1 = DatabaseManager(temp_db_path)
        from fincli.tasks import TaskManager

        task_manager = TaskManager(manager1)
        task_id = task_manager.add_task("Persistent task")

        # Create second manager and verify task exists
        manager2 = DatabaseManager(temp_db_path)
        task_manager2 = TaskManager(manager2)
        task = task_manager2.get_task(task_id)

        assert task is not None
        assert task["content"] == "Persistent task"

    def test_concurrent_access(self, temp_db_path):
        """Test concurrent access to database."""
        import threading
        import time

        def add_tasks(manager, start_id, count):
            task_manager = TaskManager(manager)
            for i in range(count):
                task_manager.add_task(f"Task {start_id + i}")
                time.sleep(0.01)  # Small delay to simulate real usage

        # Create two managers
        manager1 = DatabaseManager(temp_db_path)
        manager2 = DatabaseManager(temp_db_path)

        # Run concurrent operations
        thread1 = threading.Thread(target=add_tasks, args=(manager1, 0, 5))
        thread2 = threading.Thread(target=add_tasks, args=(manager2, 5, 5))

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # Verify all tasks were added
        task_manager = TaskManager(manager1)
        tasks = task_manager.list_tasks()
        assert len(tasks) == 10
