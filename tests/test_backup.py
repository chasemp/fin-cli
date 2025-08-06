"""
Tests for the backup system.
"""

import os
import tempfile
from pathlib import Path

import pytest

from fincli.backup import DatabaseBackup
from fincli.db import DatabaseManager
from fincli.tasks import TaskManager


class TestDatabaseBackup:
    """Test the backup system functionality."""

    def test_create_backup(self, temp_db_path):
        """Test creating a backup."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        backup_manager = DatabaseBackup(temp_db_path)

        # Add a task
        task_manager.add_task("Test task", labels=["work"])

        # Create backup
        backup_id = backup_manager.create_backup("Test backup")

        assert backup_id > 0

        # Verify backup exists
        backup_path = backup_manager._get_backup_path(backup_id)
        assert backup_path.exists()

        # Verify metadata exists
        meta_path = backup_manager._get_metadata_path(backup_id)
        assert meta_path.exists()

    def test_list_backups(self, temp_db_path):
        """Test listing backups."""
        backup_manager = DatabaseBackup(temp_db_path)

        # Create multiple backups
        backup_manager.create_backup("First backup")
        backup_manager.create_backup("Second backup")

        backups = backup_manager.list_backups()

        assert len(backups) == 2
        assert backups[0]["backup_id"] > backups[1]["backup_id"]  # Newest first

    def test_rollback(self, temp_db_path):
        """Test rolling back to a backup."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        backup_manager = DatabaseBackup(temp_db_path)

        # Add initial task
        task_manager.add_task("Original task", labels=["work"])

        # Create backup
        backup_id = backup_manager.create_backup("Initial state")

        # Add another task
        task_manager.add_task("New task", labels=["personal"])

        # Verify we have 2 tasks
        tasks = task_manager.list_tasks(include_completed=True)
        assert len(tasks) == 2

        # Rollback
        success = backup_manager.rollback(backup_id)
        assert success

        # Verify we're back to 1 task
        tasks = task_manager.list_tasks(include_completed=True)
        assert len(tasks) == 1
        assert tasks[0]["content"] == "Original task"

    def test_cleanup_old_backups(self, temp_db_path):
        """Test that old backups are cleaned up."""
        backup_manager = DatabaseBackup(temp_db_path, max_backups=3)

        # Create more backups than the limit
        for i in range(5):
            backup_manager.create_backup(f"Backup {i}")

        # Verify only 3 backups remain
        backup_ids = backup_manager._list_backup_ids()
        assert len(backup_ids) == 3
        assert max(backup_ids) == 5  # Latest backup ID
        assert min(backup_ids) == 3  # Oldest remaining backup ID
