"""
Tests for the utils module.
"""

import os
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from fincli.utils import (
    format_task_for_display,
    get_date_range,
    filter_tasks_by_date_range,
    get_editor,
)


class TestFormatTaskForDisplay:
    """Test the format_task_for_display function."""

    def test_format_open_task(self):
        """Test formatting an open task."""
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-05 10:30:00",
            "completed_at": None,
            "labels": ["work", "urgent"],
            "source": "cli",
        }
        
        result = format_task_for_display(task)
        expected = "[ ] 2025-08-05 10:30  Test task  #urgent,#work"
        
        # Split and compare parts since label order might vary
        assert "[ ] 2025-08-05 10:30  Test task" in result
        assert "#urgent" in result
        assert "#work" in result

    def test_format_completed_task(self):
        """Test formatting a completed task."""
        task = {
            "id": 1,
            "content": "Completed task",
            "created_at": "2025-08-05 10:30:00",
            "completed_at": "2025-08-05 11:45:00",
            "labels": ["personal"],
            "source": "cli",
        }
        
        result = format_task_for_display(task)
        expected = "[x] 2025-08-05 11:45  Completed task  #personal"
        
        assert result == expected

    def test_format_task_without_labels(self):
        """Test formatting a task without labels."""
        task = {
            "id": 1,
            "content": "Simple task",
            "created_at": "2025-08-05 10:30:00",
            "completed_at": None,
            "labels": None,
            "source": "cli",
        }
        
        result = format_task_for_display(task)
        expected = "[ ] 2025-08-05 10:30  Simple task"
        
        assert result == expected

    def test_format_task_with_empty_labels(self):
        """Test formatting a task with empty labels list."""
        task = {
            "id": 1,
            "content": "Task with empty labels",
            "created_at": "2025-08-05 10:30:00",
            "completed_at": None,
            "labels": [],
            "source": "cli",
        }
        
        result = format_task_for_display(task)
        expected = "[ ] 2025-08-05 10:30  Task with empty labels"
        
        assert result == expected

    def test_format_task_with_iso_timestamp(self):
        """Test formatting a task with ISO timestamp."""
        task = {
            "id": 1,
            "content": "ISO timestamp task",
            "created_at": "2025-08-05T10:30:00Z",
            "completed_at": None,
            "labels": ["test"],
            "source": "cli",
        }
        
        result = format_task_for_display(task)
        
        # Should handle ISO timestamp correctly
        assert "[ ] 2025-08-05 10:30  ISO timestamp task" in result
        assert "#test" in result


class TestGetDateRange:
    """Test the get_date_range function."""

    def test_get_date_range_default(self):
        """Test get_date_range with default parameter."""
        today, lookback = get_date_range()
        
        assert isinstance(today, date)
        assert isinstance(lookback, date)
        assert today == date.today()
        assert lookback == today - timedelta(days=1)

    def test_get_date_range_custom_days(self):
        """Test get_date_range with custom days parameter."""
        today, lookback = get_date_range(7)
        
        assert isinstance(today, date)
        assert isinstance(lookback, date)
        assert today == date.today()
        assert lookback == today - timedelta(days=7)

    def test_get_date_range_zero_days(self):
        """Test get_date_range with zero days."""
        today, lookback = get_date_range(0)
        
        assert isinstance(today, date)
        assert isinstance(lookback, date)
        assert today == date.today()
        assert lookback == today

    def test_get_date_range_large_number(self):
        """Test get_date_range with a large number."""
        today, lookback = get_date_range(365)
        
        assert isinstance(today, date)
        assert isinstance(lookback, date)
        assert today == date.today()
        assert lookback == today - timedelta(days=365)


class TestFilterTasksByDateRange:
    """Test the filter_tasks_by_date_range function."""

    def test_filter_tasks_open_tasks_always_included(self):
        """Test that open tasks are always included regardless of creation date."""
        tasks = [
            {
                "id": 1,
                "content": "Old open task",
                "created_at": "2020-01-01 10:00:00",
                "completed_at": None,
                "labels": [],
                "source": "cli",
            },
            {
                "id": 2,
                "content": "Recent open task",
                "created_at": "2025-08-05 10:00:00",
                "completed_at": None,
                "labels": [],
                "source": "cli",
            },
        ]
        
        filtered = filter_tasks_by_date_range(tasks, days=1)
        
        assert len(filtered) == 2
        assert any(task["content"] == "Old open task" for task in filtered)
        assert any(task["content"] == "Recent open task" for task in filtered)

    def test_filter_tasks_completed_tasks_filtered_by_date(self):
        """Test that completed tasks are filtered by completion date."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        
        tasks = [
            {
                "id": 1,
                "content": "Completed today",
                "created_at": "2025-08-01 10:00:00",
                "completed_at": today.strftime("%Y-%m-%d 10:00:00"),
                "labels": [],
                "source": "cli",
            },
            {
                "id": 2,
                "content": "Completed yesterday",
                "created_at": "2025-08-01 10:00:00",
                "completed_at": yesterday.strftime("%Y-%m-%d 10:00:00"),
                "labels": [],
                "source": "cli",
            },
            {
                "id": 3,
                "content": "Completed week ago",
                "created_at": "2025-08-01 10:00:00",
                "completed_at": week_ago.strftime("%Y-%m-%d 10:00:00"),
                "labels": [],
                "source": "cli",
            },
        ]
        
        # Filter for last 1 day
        filtered = filter_tasks_by_date_range(tasks, days=1)
        
        # Should include open tasks and tasks completed today/yesterday
        assert len(filtered) == 2
        assert any(task["content"] == "Completed today" for task in filtered)
        assert any(task["content"] == "Completed yesterday" for task in filtered)
        assert not any(task["content"] == "Completed week ago" for task in filtered)

    def test_filter_tasks_mixed_open_and_completed(self):
        """Test filtering with mixed open and completed tasks."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        tasks = [
            {
                "id": 1,
                "content": "Open task",
                "created_at": "2025-08-01 10:00:00",
                "completed_at": None,
                "labels": [],
                "source": "cli",
            },
            {
                "id": 2,
                "content": "Completed today",
                "created_at": "2025-08-01 10:00:00",
                "completed_at": today.strftime("%Y-%m-%d 10:00:00"),
                "labels": [],
                "source": "cli",
            },
            {
                "id": 3,
                "content": "Old completed",
                "created_at": "2025-08-01 10:00:00",
                "completed_at": "2020-01-01 10:00:00",
                "labels": [],
                "source": "cli",
            },
        ]
        
        filtered = filter_tasks_by_date_range(tasks, days=1)
        
        # Should include open task and recently completed task
        assert len(filtered) == 2
        assert any(task["content"] == "Open task" for task in filtered)
        assert any(task["content"] == "Completed today" for task in filtered)
        assert not any(task["content"] == "Old completed" for task in filtered)

    def test_filter_tasks_empty_list(self):
        """Test filtering with empty task list."""
        filtered = filter_tasks_by_date_range([], days=1)
        assert filtered == []

    def test_filter_tasks_custom_days(self):
        """Test filtering with custom days parameter."""
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        tasks = [
            {
                "id": 1,
                "content": "Completed week ago",
                "created_at": "2025-08-01 10:00:00",
                "completed_at": week_ago.strftime("%Y-%m-%d 10:00:00"),
                "labels": [],
                "source": "cli",
            },
        ]
        
        # Filter for last 7 days
        filtered = filter_tasks_by_date_range(tasks, days=7)
        
        # Should include the task completed a week ago
        assert len(filtered) == 1
        assert filtered[0]["content"] == "Completed week ago"


class TestGetEditor:
    """Test the get_editor function."""

    @patch.dict(os.environ, {"EDITOR": "vim"})
    def test_get_editor_from_environment(self):
        """Test getting editor from EDITOR environment variable."""
        result = get_editor()
        assert result == "vim"

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    def test_get_editor_fallback_to_nano(self, mock_run):
        """Test fallback to nano when no editor is found."""
        # Mock subprocess.run to return failure for all editors
        mock_run.return_value.returncode = 1
        
        result = get_editor()
        assert result == "nano"

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    def test_get_editor_fallback_to_vim(self, mock_run):
        """Test fallback to vim when nano is not found."""
        def mock_run_side_effect(cmd, **kwargs):
            class MockResult:
                def __init__(self, returncode):
                    self.returncode = returncode
            return MockResult(1 if cmd == ["which", "nano"] else 0)
        
        mock_run.side_effect = mock_run_side_effect
        
        result = get_editor()
        assert result == "vim"

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    def test_get_editor_fallback_to_code(self, mock_run):
        """Test fallback to code when nano and vim are not found."""
        def mock_run_side_effect(cmd, **kwargs):
            class MockResult:
                def __init__(self, returncode):
                    self.returncode = returncode
            return MockResult(1 if cmd[1] in ["nano", "vim"] else 0)
        
        mock_run.side_effect = mock_run_side_effect
        
        result = get_editor()
        assert result == "code" 