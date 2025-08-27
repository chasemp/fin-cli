"""
Unit tests for the sync engine.
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest

from fincli.db import DatabaseManager
from fincli.remote_models import (
    RemoteSystemType,
    RemoteTask,
    TaskAuthority,
    TaskMappingResult,
)
from fincli.sync_engine import SyncEngine
from fincli.tasks import TaskManager


class TestSyncEngine:
    """Test the SyncEngine class."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        mock_db = Mock(spec=DatabaseManager)

        # Mock the connection context manager
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.commit = Mock()

        # Create a mock context manager
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock()

        mock_db.get_connection.return_value = mock_context

        return mock_db, mock_conn, mock_cursor

    @pytest.fixture
    def mock_task_manager(self):
        """Create a mock task manager."""
        mock_tm = Mock(spec=TaskManager)
        mock_tm.add_task.return_value = 123  # Mock task ID
        return mock_tm

    @pytest.fixture
    def sync_engine(self, mock_db_manager, mock_task_manager):
        """Create a sync engine with mocked dependencies."""
        mock_db, mock_conn, mock_cursor = mock_db_manager
        return SyncEngine(mock_db, mock_task_manager)

    def test_init(self, mock_db_manager, mock_task_manager):
        """Test sync engine initialization."""
        mock_db, mock_conn, mock_cursor = mock_db_manager
        engine = SyncEngine(mock_db, mock_task_manager)

        assert engine.db_manager == mock_db
        assert engine.task_manager == mock_task_manager

    def test_sync_remote_tasks_success(self, sync_engine, mock_db_manager, mock_task_manager):
        """Test successful sync of remote tasks."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Mock cursor results
        mock_cursor.fetchone.return_value = None  # No existing task

        # Create test remote tasks
        remote_tasks = [RemoteTask(remote_id="TEST-001", remote_source="google_sheets", content="Test task 1"), RemoteTask(remote_id="TEST-002", remote_source="google_sheets", content="Test task 2")]

        # Mock task manager add_task
        mock_task_manager.add_task.return_value = 123

        # Test sync
        results = sync_engine.sync_remote_tasks(remote_tasks, RemoteSystemType.GOOGLE_SHEETS, dry_run=False)

        # Verify results
        assert results["total_tasks"] == 2
        assert results["tasks_imported"] == 2
        assert results["tasks_updated"] == 0
        assert results["tasks_skipped"] == 0
        assert len(results["errors"]) == 0
        assert results["dry_run"] is False

    def test_sync_remote_tasks_dry_run(self, sync_engine, mock_db_manager, mock_task_manager):
        """Test dry run sync of remote tasks."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Create test remote tasks
        remote_tasks = [RemoteTask(remote_id="TEST-001", remote_source="google_sheets", content="Test task 1")]

        # Test dry run sync
        results = sync_engine.sync_remote_tasks(remote_tasks, RemoteSystemType.GOOGLE_SHEETS, dry_run=True)

        # Verify results
        assert results["total_tasks"] == 1
        assert results["tasks_imported"] == 1
        assert results["tasks_updated"] == 0
        assert results["tasks_skipped"] == 0
        assert len(results["errors"]) == 0
        assert results["dry_run"] is True

        # Verify no actual database changes were made
        mock_task_manager.add_task.assert_not_called()

    def test_sync_remote_tasks_with_existing_task(self, sync_engine, mock_db_manager, mock_task_manager):
        """Test sync when task already exists locally."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Mock cursor to return existing task ID
        mock_cursor.fetchone.return_value = (456,)  # Existing task ID

        # Create test remote task
        remote_tasks = [RemoteTask(remote_id="TEST-001", remote_source="google_sheets", content="Test task 1")]

        # Test sync
        results = sync_engine.sync_remote_tasks(remote_tasks, RemoteSystemType.GOOGLE_SHEETS, dry_run=False)

        # Verify results
        assert results["total_tasks"] == 1
        assert results["tasks_imported"] == 0
        assert results["tasks_updated"] == 1
        assert results["tasks_skipped"] == 0
        assert len(results["errors"]) == 0

    def test_sync_remote_tasks_with_validation_error(self, sync_engine, mock_db_manager, mock_task_manager):
        """Test sync with invalid remote task."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Create invalid remote task (missing content) - need to bypass validation
        from unittest.mock import Mock

        mock_task = Mock()
        mock_task.remote_id = "TEST-001"
        mock_task.remote_source = "google_sheets"
        mock_task.content = ""
        mock_task.authority = None

        # Mock the validation to fail
        with pytest.MonkeyPatch().context() as m:
            m.setattr("fincli.sync_engine.RemoteTaskValidator.is_valid", lambda x: False)
            m.setattr("fincli.sync_engine.RemoteTaskValidator.validate_remote_task", lambda x: ["content is required"])

            # Test sync
            results = sync_engine.sync_remote_tasks([mock_task], RemoteSystemType.GOOGLE_SHEETS, dry_run=False)

            # Verify results
            assert results["total_tasks"] == 1
            assert results["tasks_imported"] == 0
            assert results["tasks_updated"] == 0
            assert results["tasks_skipped"] == 1
            assert len(results["errors"]) == 1
            assert "Validation failed" in results["errors"][0]

    def test_find_existing_remote_task_found(self, sync_engine, mock_db_manager):
        """Test finding existing remote task."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Mock cursor to return existing task
        mock_cursor.fetchone.return_value = (789,)

        # Test finding existing task
        task_id = sync_engine._find_existing_remote_task("TEST-001", "google_sheets")

        assert task_id == 789

        # Verify correct SQL was executed
        mock_cursor.execute.assert_called_once_with("SELECT id FROM tasks WHERE remote_id = ? AND remote_source = ?", ("TEST-001", "google_sheets"))

    def test_find_existing_remote_task_not_found(self, sync_engine, mock_db_manager):
        """Test finding non-existent remote task."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Mock cursor to return no results
        mock_cursor.fetchone.return_value = None

        # Test finding non-existent task
        task_id = sync_engine._find_existing_remote_task("TEST-999", "google_sheets")

        assert task_id is None

    def test_import_new_task_success(self, sync_engine, mock_db_manager, mock_task_manager):
        """Test successful import of new task."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Create test remote task and mapping result
        remote_task = RemoteTask(remote_id="TEST-001", remote_source="google_sheets", content="Test task content")

        mapping_result = TaskMappingResult(success=True, local_content="Test task content #remote", local_labels=["work", "urgent"], should_purge_remote=True, should_update_remote_status=False)

        # Mock task manager
        mock_task_manager.add_task.return_value = 123

        # Test import
        result = sync_engine._import_new_task(remote_task, mapping_result, dry_run=False)

        # Verify result
        assert result["action"] == "imported"
        assert result["reason"] == "New task imported"
        assert result["task_id"] == 123
        assert result["content"] == "Test task content #remote"
        assert result["labels"] == ["work", "urgent"]

        # Verify task manager was called
        mock_task_manager.add_task.assert_called_once_with(content="Test task content #remote", labels="work,urgent", source="remote_sync", due_date=None, context="default")

    def test_import_new_task_dry_run(self, sync_engine, mock_db_manager, mock_task_manager):
        """Test dry run import of new task."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Create test remote task and mapping result
        remote_task = RemoteTask(remote_id="TEST-001", remote_source="google_sheets", content="Test task content")

        mapping_result = TaskMappingResult(success=True, local_content="Test task content #remote", local_labels=["work"], should_purge_remote=True, should_update_remote_status=False)

        # Test dry run import
        result = sync_engine._import_new_task(remote_task, mapping_result, dry_run=True)

        # Verify result
        assert result["action"] == "imported"
        assert result["reason"] == "Dry run - would import new task"
        assert result["task_id"] is None
        assert result["content"] == "Test task content #remote"
        assert result["labels"] == ["work"]

        # Verify task manager was not called
        mock_task_manager.add_task.assert_not_called()

    def test_update_existing_task_success(self, sync_engine, mock_db_manager, mock_task_manager):
        """Test successful update of existing task."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Create test remote task and mapping result
        remote_task = RemoteTask(remote_id="TEST-001", remote_source="google_sheets", content="Updated task content")

        mapping_result = TaskMappingResult(success=True, local_content="Updated task content #remote", local_labels=["work"], should_purge_remote=True, should_update_remote_status=False)

        # Test update
        result = sync_engine._update_existing_task(456, remote_task, mapping_result, dry_run=False)

        # Verify result
        assert result["action"] == "updated"
        assert result["reason"] == "Existing task updated"
        assert result["task_id"] == 456
        assert result["content"] == "Updated task content #remote"

        # Verify database was updated
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()

    def test_get_sync_status(self, sync_engine, mock_db_manager):
        """Test getting sync status."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Mock cursor results for sync status
        mock_cursor.fetchall.return_value = [
            ("full", False, 5),  # 5 full authority tasks
            ("status_only", True, 3),  # 3 shadow tasks
        ]
        mock_cursor.fetchone.side_effect = [(8,), (15,), ("2024-01-15 10:30:00",)]  # total_remote_tasks  # total_tasks  # last_sync

        # Test getting sync status
        status = sync_engine.get_sync_status()

        # Verify status
        assert status["total_tasks"] == 15
        assert status["total_remote_tasks"] == 8
        assert status["remote_tasks_by_authority"]["full_False"]["count"] == 5
        assert status["remote_tasks_by_authority"]["status_only_True"]["count"] == 3
        assert status["last_sync_info"]["last_sync"] == "2024-01-15 10:30:00"

    def test_get_sync_status_by_source(self, sync_engine, mock_db_manager):
        """Test getting sync status filtered by source."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Mock cursor results for specific source
        mock_cursor.fetchall.return_value = [
            ("full", False, 3),  # 3 full authority tasks from google_sheets
        ]
        mock_cursor.fetchone.side_effect = [(3,), (15,), ("2024-01-15 10:30:00",)]  # total_remote_tasks from google_sheets (filtered by source)  # total_tasks (filtered by source)  # last_sync

        # Test getting sync status for specific source
        status = sync_engine.get_sync_status(remote_source="google_sheets")

        # Verify status
        assert status["total_tasks"] == 15
        assert status["total_remote_tasks"] == 3
        assert status["remote_tasks_by_authority"]["full_False"]["count"] == 3

    def test_cleanup_remote_tasks(self, sync_engine, mock_db_manager):
        """Test cleanup of remote tasks."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Mock cursor results for cleanup
        mock_cursor.fetchall.return_value = [
            (123, "TEST-001", "Task 1", "full"),
            (456, "TEST-002", "Task 2", "full"),
        ]

        # Test cleanup
        results = sync_engine.cleanup_remote_tasks("google_sheets", dry_run=False)

        # Verify results
        assert results["total_tasks"] == 2
        assert results["tasks_cleaned"] == 2
        assert len(results["errors"]) == 0
        assert results["dry_run"] is False

        # Verify database was updated
        assert mock_cursor.execute.call_count >= 2  # At least 2 UPDATE calls
        mock_conn.commit.assert_called()

    def test_cleanup_remote_tasks_dry_run(self, sync_engine, mock_db_manager):
        """Test dry run cleanup of remote tasks."""
        mock_db, mock_conn, mock_cursor = mock_db_manager

        # Mock cursor results for cleanup
        mock_cursor.fetchall.return_value = [
            (123, "TEST-001", "Task 1", "full"),
        ]

        # Test dry run cleanup
        results = sync_engine.cleanup_remote_tasks("google_sheets", dry_run=True)

        # Verify results
        assert results["total_tasks"] == 1
        assert results["tasks_cleaned"] == 1
        assert len(results["errors"]) == 0
        assert results["dry_run"] is True

        # Verify no database changes were made
        mock_conn.commit.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
