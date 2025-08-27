"""
Unit tests for remote task models and authority system.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from fincli.remote_models import RemoteSystemType, RemoteTask, RemoteTaskValidator, TaskAuthority, TaskMapper, TaskMappingResult, create_confluence_task, create_google_sheets_task


class TestTaskAuthority:
    """Test the TaskAuthority enum."""

    def test_enum_values(self):
        """Test enum values are correct."""
        assert TaskAuthority.FULL_AUTHORITY.value == "full"
        assert TaskAuthority.STATUS_ONLY_AUTHORITY.value == "status_only"

    def test_enum_membership(self):
        """Test enum membership."""
        assert TaskAuthority.FULL_AUTHORITY in TaskAuthority
        assert TaskAuthority.STATUS_ONLY_AUTHORITY in TaskAuthority
        assert "invalid" not in [e.value for e in TaskAuthority]


class TestRemoteSystemType:
    """Test the RemoteSystemType enum."""

    def test_enum_values(self):
        """Test enum values are correct."""
        assert RemoteSystemType.GOOGLE_SHEETS.value == "google_sheets"
        assert RemoteSystemType.CONFLUENCE.value == "confluence"
        assert RemoteSystemType.JIRA.value == "jira"
        assert RemoteSystemType.SLACK.value == "slack"
        assert RemoteSystemType.EMAIL.value == "email"


class TestRemoteTask:
    """Test the RemoteTask dataclass."""

    def test_create_valid_task(self):
        """Test creating a valid remote task."""
        task = RemoteTask(remote_id="TEST-001", remote_source="test_system", content="Test task content")

        assert task.remote_id == "TEST-001"
        assert task.remote_source == "test_system"
        assert task.content == "Test task content"
        assert task.authority == TaskAuthority.FULL_AUTHORITY
        assert task.is_shadow_task is False
        assert task.sync_status == "pending"

    def test_create_status_authority_task(self):
        """Test creating a status authority task."""
        task = RemoteTask(remote_id="TEST-002", remote_source="confluence", content="Test task content", authority=TaskAuthority.STATUS_ONLY_AUTHORITY)

        assert task.authority == TaskAuthority.STATUS_ONLY_AUTHORITY
        assert task.is_shadow_task is True

    def test_missing_required_fields(self):
        """Test that missing required fields raise errors."""
        # Test with empty strings (which will fail validation)
        with pytest.raises(ValueError, match="remote_id is required"):
            RemoteTask(remote_id="", remote_source="test_system", content="Test task content")

        with pytest.raises(ValueError, match="remote_source is required"):
            RemoteTask(remote_id="TEST-001", remote_source="", content="Test task content")

        with pytest.raises(ValueError, match="content is required"):
            RemoteTask(remote_id="TEST-001", remote_source="test_system", content="")

    def test_auto_set_shadow_task(self):
        """Test that is_shadow_task is automatically set for status authority."""
        task = RemoteTask(remote_id="TEST-003", remote_source="confluence", content="Test task content", authority=TaskAuthority.STATUS_ONLY_AUTHORITY)

        assert task.is_shadow_task is True


class TestTaskMappingResult:
    """Test the TaskMappingResult dataclass."""

    def test_create_success_result(self):
        """Test creating a successful mapping result."""
        result = TaskMappingResult(success=True, local_content="Local task content #remote", local_labels=["work", "urgent"])

        assert result.success is True
        assert result.local_content == "Local task content #remote"
        assert result.local_labels == ["work", "urgent"]
        assert result.error_message is None
        assert result.should_purge_remote is False
        assert result.should_update_remote_status is False

    def test_create_failure_result(self):
        """Test creating a failed mapping result."""
        result = TaskMappingResult(success=False, local_content="", local_labels=[], error_message="Validation failed")

        assert result.success is False
        assert result.local_content == ""
        assert result.local_labels == []
        assert result.error_message == "Validation failed"


class TestTaskMapper:
    """Test the TaskMapper class."""

    def test_init_google_sheets(self):
        """Test initializing mapper for Google Sheets."""
        mapper = TaskMapper(RemoteSystemType.GOOGLE_SHEETS)
        assert mapper.system_type == RemoteSystemType.GOOGLE_SHEETS
        assert mapper.default_authority == TaskAuthority.FULL_AUTHORITY

    def test_init_confluence(self):
        """Test initializing mapper for Confluence."""
        mapper = TaskMapper(RemoteSystemType.CONFLUENCE)
        assert mapper.system_type == RemoteSystemType.CONFLUENCE
        assert mapper.default_authority == TaskAuthority.STATUS_ONLY_AUTHORITY

    def test_map_full_authority_task(self):
        """Test mapping a full authority task."""
        mapper = TaskMapper(RemoteSystemType.GOOGLE_SHEETS)

        remote_task = RemoteTask(remote_id="TEST-001", remote_source="google_sheets", content="Test task content")

        result = mapper.map_remote_task(remote_task)

        assert result.success is True
        assert "Test task content" in result.local_content
        assert "#remote" in result.local_content
        assert "#shadow" not in result.local_content
        assert result.should_purge_remote is True
        assert result.should_update_remote_status is False
        assert "authority:full" in result.local_labels
        assert "source:google_sheets" in result.local_labels

    def test_map_status_authority_task(self):
        """Test mapping a status authority task."""
        mapper = TaskMapper(RemoteSystemType.CONFLUENCE)

        remote_task = RemoteTask(remote_id="TEST-002", remote_source="confluence", content="Test task content")

        result = mapper.map_remote_task(remote_task)

        assert result.success is True
        assert "Test task content" in result.local_content
        assert "#remote" in result.local_content
        assert "#shadow" in result.local_content
        assert result.should_purge_remote is False
        assert result.should_update_remote_status is True
        assert "authority:status" in result.local_labels
        assert "source:confluence" in result.local_labels

    def test_map_task_with_custom_labels(self):
        """Test mapping a task with custom labels."""
        mapper = TaskMapper(RemoteSystemType.GOOGLE_SHEETS)

        remote_task = RemoteTask(remote_id="TEST-003", remote_source="google_sheets", content="Test task content", labels=["custom", "label"])

        result = mapper.map_remote_task(remote_task)

        assert result.success is True
        assert "custom" in result.local_labels
        assert "label" in result.local_labels
        assert "source:google_sheets" in result.local_labels
        assert "authority:full" in result.local_labels

    def test_map_task_with_existing_authority(self):
        """Test mapping a task that already has authority set."""
        mapper = TaskMapper(RemoteSystemType.GOOGLE_SHEETS)

        remote_task = RemoteTask(remote_id="TEST-004", remote_source="google_sheets", content="Test task content", authority=TaskAuthority.STATUS_ONLY_AUTHORITY)

        result = mapper.map_remote_task(remote_task)

        assert result.success is True
        # The system type (Google Sheets) determines the authority, not the explicit setting
        assert result.should_purge_remote is True
        assert result.should_update_remote_status is False


class TestRemoteTaskValidator:
    """Test the RemoteTaskValidator class."""

    def test_validate_valid_task(self):
        """Test validating a valid task."""
        task = RemoteTask(remote_id="TEST-001", remote_source="test_system", content="Test task content")

        errors = RemoteTaskValidator.validate_remote_task(task)
        assert len(errors) == 0
        assert RemoteTaskValidator.is_valid(task) is True

    def test_validate_missing_fields(self):
        """Test validating a task with missing fields."""
        # Create a mock task with empty fields to test validation
        mock_task = Mock()
        mock_task.remote_id = ""
        mock_task.remote_source = ""
        mock_task.content = ""
        mock_task.authority = None

        errors = RemoteTaskValidator.validate_remote_task(mock_task)
        assert len(errors) == 3
        assert "remote_id is required" in errors
        assert "remote_source is required" in errors
        assert "content is required" in errors
        assert RemoteTaskValidator.is_valid(mock_task) is False

    def test_validate_invalid_authority(self):
        """Test validating a task with invalid authority."""
        task = RemoteTask(remote_id="TEST-001", remote_source="test_system", content="Test task content")
        # Manually set invalid authority
        task.authority = "invalid"

        errors = RemoteTaskValidator.validate_remote_task(task)
        assert len(errors) == 1
        assert "Invalid authority" in errors[0]

    def test_validate_content_too_long(self):
        """Test validating a task with content too long."""
        long_content = "x" * 1501
        task = RemoteTask(remote_id="TEST-001", remote_source="test_system", content=long_content)

        errors = RemoteTaskValidator.validate_remote_task(task)
        assert len(errors) == 1
        assert "Content too long" in errors[0]

    def test_validate_remote_id_too_long(self):
        """Test validating a task with remote ID too long."""
        long_id = "x" * 101
        task = RemoteTask(remote_id=long_id, remote_source="test_system", content="Test task content")

        errors = RemoteTaskValidator.validate_remote_task(task)
        assert len(errors) == 1
        assert "Remote ID too long" in errors[0]


class TestFactoryFunctions:
    """Test the factory functions for creating remote tasks."""

    def test_create_google_sheets_task(self):
        """Test creating a Google Sheets task."""
        task = create_google_sheets_task(remote_id="RUN001", content="", user_name="John Doe", text="Review security report", permalink="http://example.com")

        assert task.remote_id == "RUN001"
        assert task.remote_source == "google_sheets"
        assert "John Doe" in task.content
        assert "Review security report" in task.content
        assert "http://example.com" in task.content
        assert task.authority == TaskAuthority.FULL_AUTHORITY
        assert task.is_shadow_task is False

    def test_create_google_sheets_task_with_content(self):
        """Test creating a Google Sheets task with pre-formatted content."""
        task = create_google_sheets_task(remote_id="RUN002", content="Pre-formatted content")

        assert task.content == "Pre-formatted content"
        assert task.authority == TaskAuthority.FULL_AUTHORITY

    def test_create_confluence_task(self):
        """Test creating a Confluence task."""
        task = create_confluence_task(remote_id="CONF-123", content="Update API documentation", remote_status="in_progress")

        assert task.remote_id == "CONF-123"
        assert task.remote_source == "confluence"
        assert task.content == "Update API documentation"
        assert task.remote_status == "in_progress"
        assert task.authority == TaskAuthority.STATUS_ONLY_AUTHORITY
        assert task.is_shadow_task is True


if __name__ == "__main__":
    pytest.main([__file__])
