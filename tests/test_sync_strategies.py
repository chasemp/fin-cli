"""
Tests for sync strategies module.
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from fincli.remote_models import (
    RemoteSystemType,
    RemoteTask,
    TaskAuthority,
    create_google_sheets_task,
)
from fincli.sync_engine import SyncEngine
from fincli.sync_strategies import (
    ConfluenceSyncStrategy,
    GoogleSheetsSyncStrategy,
    SyncStrategyFactory,
)


class TestGoogleSheetsSyncStrategy:
    """Test GoogleSheetsSyncStrategy class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_sync_engine = Mock(spec=SyncEngine)
        self.mock_sheets_reader = Mock()
        self.strategy = GoogleSheetsSyncStrategy(self.mock_sync_engine, self.mock_sheets_reader)

    def test_init(self):
        """Test strategy initialization."""
        assert self.strategy.sync_engine == self.mock_sync_engine
        assert self.strategy.sheets_reader == self.mock_sheets_reader
        assert self.strategy.system_type == RemoteSystemType.GOOGLE_SHEETS

    def test_sync_sheet_tasks_no_rows(self):
        """Test sync when sheet has no rows."""
        self.mock_sheets_reader.read_all_rows.return_value = []

        result = self.strategy.sync_sheet_tasks("todo", dry_run=False)

        assert result["success"] is True
        assert result["sheet_name"] == "todo"
        assert result["total_rows"] == 0
        assert result["tasks_processed"] == 0
        assert result["dry_run"] is False
        assert "message" in result

    def test_sync_sheet_tasks_with_rows(self):
        """Test sync when sheet has rows."""
        # Mock sheet data
        mock_rows = [["Source", "RunID", "Ts Time", "User Name", "Text", "Permalink"], ["test", "123", "2024-01-01", "John", "Test task", "http://example.com"]]

        # Mock remote tasks
        mock_remote_tasks = [create_google_sheets_task(remote_id="123", content="John: Test task #remote", user_name="John", text="Test task", permalink="http://example.com", source="test", remote_metadata={"row_number": 2})]

        # Mock sync engine results
        mock_sync_results = {"tasks_imported": 1, "tasks_updated": 0, "tasks_skipped": 0, "errors": []}

        self.mock_sheets_reader.read_all_rows.return_value = mock_rows
        self.mock_sheets_reader.parse_task_data.return_value = mock_remote_tasks
        self.mock_sync_engine.sync_remote_tasks.return_value = mock_sync_results

        result = self.strategy.sync_sheet_tasks("todo", dry_run=False)

        assert result["success"] is True
        assert result["sheet_name"] == "todo"
        assert result["total_rows"] == 2
        assert result["tasks_imported"] == 1
        assert "purge_results" in result

    def test_sync_sheet_tasks_dry_run(self):
        """Test sync in dry run mode."""
        mock_rows = [["Source", "RunID", "Ts Time", "User Name", "Text", "Permalink"], ["test", "123", "2024-01-01", "John", "Test task", "http://example.com"]]

        mock_remote_tasks = [create_google_sheets_task(remote_id="123", content="John: Test task #remote", user_name="John", text="Test task", permalink="http://example.com", source="test", remote_metadata={"row_number": 2})]

        mock_sync_results = {"tasks_imported": 1, "tasks_updated": 0, "tasks_skipped": 0, "errors": []}

        self.mock_sheets_reader.read_all_rows.return_value = mock_rows
        self.mock_sheets_reader.parse_task_data.return_value = mock_remote_tasks
        self.mock_sync_engine.sync_remote_tasks.return_value = mock_sync_results

        result = self.strategy.sync_sheet_tasks("todo", dry_run=True)

        assert result["dry_run"] is True
        assert "purge_results" not in result  # No purging in dry run

    def test_sync_sheet_tasks_error_handling(self):
        """Test error handling during sync."""
        self.mock_sheets_reader.read_all_rows.side_effect = Exception("API Error")

        result = self.strategy.sync_sheet_tasks("todo", dry_run=False)

        assert result["success"] is False
        assert "error" in result
        assert "API Error" in result["error"]

    def test_purge_remote_tasks_success(self):
        """Test successful remote task purging."""
        remote_tasks = [create_google_sheets_task(remote_id="123", content="Task 1", user_name="John", text="Task 1", permalink="http://example.com", source="test", remote_metadata={"row_number": 2}), create_google_sheets_task(remote_id="456", content="Task 2", user_name="Jane", text="Task 2", permalink="http://example.com", source="test", remote_metadata={"row_number": 3})]

        # Mock successful batch deletion
        self.mock_sheets_reader.batch_delete_rows.return_value = {"success": True, "deleted_rows": 2, "deleted_row_numbers": [3, 2], "errors": []}

        result = self.strategy._purge_remote_tasks(remote_tasks, "todo")

        assert result["total_tasks"] == 2
        assert result["tasks_purged"] == 2
        assert result["errors"] == []
        assert result["sheet_name"] == "todo"

    def test_purge_remote_tasks_no_row_numbers(self):
        """Test purging when no row numbers are available."""
        remote_tasks = [create_google_sheets_task(remote_id="123", content="Task 1", user_name="John", text="Task 1", permalink="http://example.com", source="test", remote_metadata={})]  # No row number

        result = self.strategy._purge_remote_tasks(remote_tasks, "todo")

        assert result["total_tasks"] == 1
        assert result["tasks_purged"] == 0
        assert result["errors"] == []

    def test_purge_remote_tasks_batch_failure(self):
        """Test handling of batch deletion failure."""
        remote_tasks = [create_google_sheets_task(remote_id="123", content="Task 1", user_name="John", text="Task 1", permalink="http://example.com", source="test", remote_metadata={"row_number": 2})]

        # Mock batch deletion failure
        self.mock_sheets_reader.batch_delete_rows.return_value = {"success": False, "deleted_rows": 0, "errors": ["API quota exceeded"]}

        result = self.strategy._purge_remote_tasks(remote_tasks, "todo")

        assert result["total_tasks"] == 1
        assert result["tasks_purged"] == 0
        assert len(result["errors"]) > 0

    def test_get_sync_status(self):
        """Test getting sync status."""
        # Mock sync engine status
        mock_status = {"full_False": {"count": 5, "last_sync": "2024-01-01T10:00:00"}, "status_only_True": {"count": 2, "last_sync": "2024-01-01T09:00:00"}}

        # Mock sheet info
        mock_sheet_info = {"title": "Test Sheet", "sheets": [{"name": "todo"}, {"name": "done"}]}

        self.mock_sync_engine.get_sync_status.return_value = mock_status
        self.mock_sheets_reader.get_sheet_info.return_value = mock_sheet_info

        result = self.strategy.get_sync_status("todo")

        assert result["system_type"] == "google_sheets"
        assert result["sheet_name"] == "todo"
        assert "sheet_info" in result
        assert result["sheet_info"]["title"] == "Test Sheet"

    def test_validate_sheet_structure_valid(self):
        """Test validation of valid sheet structure."""
        mock_rows = [["Source", "RunID", "Ts Time", "User Name", "Text", "Permalink"], ["test", "123", "2024-01-01", "John", "Test task", "http://example.com"]]

        mock_remote_tasks = [create_google_sheets_task(remote_id="123", content="John: Test task #remote", user_name="John", text="Test task", permalink="http://example.com", source="test", remote_metadata={"row_number": 2})]

        self.mock_sheets_reader.read_all_rows.return_value = mock_rows
        self.mock_sheets_reader.parse_task_data.return_value = mock_remote_tasks

        result = self.strategy.validate_sheet_structure("todo")

        assert result["valid"] is True
        assert result["sheet_name"] == "todo"
        assert result["total_rows"] == 2
        assert result["valid_tasks_found"] == 1

    def test_validate_sheet_structure_missing_headers(self):
        """Test validation when required headers are missing."""
        mock_rows = [["Source", "RunID"], ["test", "123"]]  # Missing User Name and Text

        self.mock_sheets_reader.read_all_rows.return_value = mock_rows

        result = self.strategy.validate_sheet_structure("todo")

        assert result["valid"] is False
        assert "missing_headers" in result
        assert "user_name" in result["missing_headers"]
        assert "text" in result["missing_headers"]

    def test_validate_sheet_structure_empty_sheet(self):
        """Test validation of empty sheet."""
        self.mock_sheets_reader.read_all_rows.return_value = []

        result = self.strategy.validate_sheet_structure("todo")

        assert result["valid"] is False
        assert "error" in result
        assert "empty" in result["error"].lower()


class TestConfluenceSyncStrategy:
    """Test ConfluenceSyncStrategy class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_sync_engine = Mock(spec=SyncEngine)
        self.strategy = ConfluenceSyncStrategy(self.mock_sync_engine)

    def test_init(self):
        """Test strategy initialization."""
        assert self.strategy.sync_engine == self.mock_sync_engine
        assert self.strategy.system_type == RemoteSystemType.CONFLUENCE

    def test_sync_confluence_tasks_not_implemented(self):
        """Test that Confluence sync is not yet implemented."""
        result = self.strategy.sync_confluence_tasks("TEST", dry_run=False)

        assert result["success"] is False
        assert result["system_type"] == "confluence"
        assert result["space_key"] == "TEST"
        assert "not yet implemented" in result["error"]


class TestSyncStrategyFactory:
    """Test SyncStrategyFactory class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_sync_engine = Mock(spec=SyncEngine)
        self.mock_sheets_reader = Mock()

    def test_create_google_sheets_strategy(self):
        """Test creating Google Sheets sync strategy."""
        strategy = SyncStrategyFactory.create_strategy(RemoteSystemType.GOOGLE_SHEETS, self.mock_sync_engine, sheets_reader=self.mock_sheets_reader)

        assert isinstance(strategy, GoogleSheetsSyncStrategy)
        assert strategy.sync_engine == self.mock_sync_engine
        assert strategy.sheets_reader == self.mock_sheets_reader

    def test_create_google_sheets_strategy_missing_reader(self):
        """Test creating Google Sheets strategy without required sheets_reader."""
        with pytest.raises(ValueError, match="sheets_reader is required"):
            SyncStrategyFactory.create_strategy(RemoteSystemType.GOOGLE_SHEETS, self.mock_sync_engine)

    def test_create_confluence_strategy(self):
        """Test creating Confluence sync strategy."""
        strategy = SyncStrategyFactory.create_strategy(RemoteSystemType.CONFLUENCE, self.mock_sync_engine)

        assert isinstance(strategy, ConfluenceSyncStrategy)
        assert strategy.sync_engine == self.mock_sync_engine

    def test_create_unsupported_strategy(self):
        """Test creating strategy for unsupported system type."""
        with pytest.raises(ValueError, match="Unsupported system type"):
            SyncStrategyFactory.create_strategy("UNSUPPORTED", self.mock_sync_engine)  # type: ignore
