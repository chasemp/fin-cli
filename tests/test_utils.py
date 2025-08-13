"""
Tests for the utils module.
"""

import os
from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest

from fincli.utils import (
    filter_tasks_by_date_range,
    format_task_for_display,
    get_date_range,
    get_editor,
    is_important_task,
    is_today_task,
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
        expected = "1 [x] 2025-08-05 11:45  Completed task  #personal"

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
        expected = "1 [ ] 2025-08-05 10:30  Simple task"

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
        expected = "1 [ ] 2025-08-05 10:30  Task with empty labels"

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


class TestIsImportantTask:
    """Test the is_important_task function."""

    def test_important_task_with_i(self):
        """Test that task with i label is marked as important."""
        task = {
            "id": 1,
            "content": "Important task",
            "created_at": "2025-08-05 10:30:00",
            "completed_at": None,
            "labels": ["i", "work"],
            "source": "cli",
        }

        assert is_important_task(task) is True

    def test_non_important_task(self):
        """Test that task without i label is not important."""
        task = {
            "id": 1,
            "content": "Regular task",
            "created_at": "2025-08-05 10:30:00",
            "completed_at": None,
            "labels": ["work", "urgent"],
            "source": "cli",
        }

        assert is_important_task(task) is False

    def test_task_without_labels(self):
        """Test that task without labels is not important."""
        task = {
            "id": 1,
            "content": "Task without labels",
            "created_at": "2025-08-05 10:30:00",
            "completed_at": None,
            "labels": None,
            "source": "cli",
        }

        assert is_important_task(task) is False

    def test_task_with_empty_labels(self):
        """Test that task with empty labels list is not important."""
        task = {
            "id": 1,
            "content": "Task with empty labels",
            "created_at": "2025-08-05 10:30:00",
            "completed_at": None,
            "labels": [],
            "source": "cli",
        }

        assert is_important_task(task) is False


class TestIsTodayTask:
    """Test the is_today_task function."""

    def test_today_task_with_t(self):
        """Test that task with t label is marked as today."""
        task = {
            "id": 1,
            "content": "Today task",
            "created_at": "2025-08-05 10:30:00",
            "completed_at": None,
            "labels": ["t", "work"],
            "source": "cli",
        }

        assert is_today_task(task) is True

    def test_non_today_task(self):
        """Test that task without t label is not today."""
        task = {
            "id": 1,
            "content": "Regular task",
            "created_at": "2025-08-05 10:30:00",
            "completed_at": None,
            "labels": ["work", "urgent"],
            "source": "cli",
        }

        assert is_today_task(task) is False

    def test_task_without_labels(self):
        """Test that task without labels is not today."""
        task = {
            "id": 1,
            "content": "Task without labels",
            "created_at": "2025-08-05 10:30:00",
            "completed_at": None,
            "labels": None,
            "source": "cli",
        }

        assert is_today_task(task) is False

    def test_task_with_empty_labels(self):
        """Test that task with empty labels list is not today."""
        task = {
            "id": 1,
            "content": "Task with empty labels",
            "created_at": "2025-08-05 10:30:00",
            "completed_at": None,
            "labels": [],
            "source": "cli",
        }

        assert is_today_task(task) is False


class TestGetDateRange:
    """Test the get_date_range function."""

    def test_default_range(self):
        """Test default date range (1 day)."""
        today, lookback = get_date_range()

        assert today == date.today()
        assert lookback == date.today() - timedelta(days=1)

    def test_custom_range(self, weekdays_only_disabled):
        """Test custom date range."""
        today, lookback = get_date_range(7, weekdays_only=False)

        assert today == date.today()
        assert lookback == date.today() - timedelta(days=7)

    def test_zero_days(self):
        """Test zero days range."""
        today, lookback = get_date_range(0)

        assert today == date.today()
        assert lookback is None  # None indicates no date restriction (all time)


class TestFilterTasksByDateRange:
    """Test the filter_tasks_by_date_range function."""

    def test_filter_open_tasks_always_included(self, weekdays_only_disabled):
        """Test that open tasks are always included regardless of date."""
        from datetime import date, timedelta

        today = date.today()
        yesterday = today - timedelta(days=1)

        tasks = [
            {
                "id": 1,
                "content": "Old open task",
                "created_at": f"{yesterday} 10:00:00",
                "completed_at": None,
                "labels": [],
                "source": "cli",
            },
            {
                "id": 2,
                "content": "Recent open task",
                "created_at": f"{today} 10:00:00",
                "completed_at": None,
                "labels": [],
                "source": "cli",
            },
        ]

        filtered = filter_tasks_by_date_range(tasks, days=1, weekdays_only=False)

        # Both open tasks should be included
        assert len(filtered) == 2
        assert filtered[0]["id"] == 1  # Old task first (by creation date)
        assert filtered[1]["id"] == 2  # Recent task second

    def test_filter_completed_tasks_by_date(self, weekdays_only_disabled):
        """Test that completed tasks are filtered by completion date."""
        from datetime import date, timedelta

        today = date.today()
        yesterday = today - timedelta(days=1)

        tasks = [
            {
                "id": 1,
                "content": "Old completed task",
                "created_at": f"{yesterday - timedelta(days=10)} 10:00:00",
                "completed_at": f"{yesterday - timedelta(days=10)} 11:00:00",
                "labels": [],
                "source": "cli",
            },
            {
                "id": 2,
                "content": "Recent completed task",
                "created_at": f"{yesterday} 10:00:00",
                "completed_at": f"{yesterday} 11:00:00",
                "labels": [],
                "source": "cli",
            },
        ]

        filtered = filter_tasks_by_date_range(tasks, days=1, weekdays_only=False)

        # Only recent completed task should be included
        assert len(filtered) == 1
        assert filtered[0]["id"] == 2

    def test_priority_sorting(self, weekdays_only_disabled):
        """Test that important and today tasks appear in correct order."""
        from datetime import date, timedelta

        today = date.today()
        yesterday = today - timedelta(days=1)

        tasks = [
            {
                "id": 1,
                "content": "Regular task",
                "created_at": f"{yesterday} 10:00:00",
                "completed_at": None,
                "labels": [],
                "source": "cli",
            },
            {
                "id": 2,
                "content": "Today task",
                "created_at": f"{today} 10:00:00",
                "completed_at": None,
                "labels": ["t"],
                "source": "cli",
            },
            {
                "id": 3,
                "content": "Important task",
                "created_at": f"{yesterday} 09:00:00",
                "completed_at": None,
                "labels": ["i", "urgent"],
                "source": "cli",
            },
            {
                "id": 4,
                "content": "Important today task",
                "created_at": f"{today} 09:00:00",
                "completed_at": None,
                "labels": ["i", "t"],
                "source": "cli",
            },
        ]

        filtered = filter_tasks_by_date_range(tasks, days=1, weekdays_only=False)

        # Important tasks first, then today tasks, then regular tasks
        # Tasks with both #i and #t come before tasks with only #i
        assert len(filtered) == 4
        assert filtered[0]["id"] == 4  # Important today task first
        assert filtered[1]["id"] == 3  # Important task second
        assert filtered[2]["id"] == 2  # Today task third
        assert filtered[3]["id"] == 1  # Regular task last

    def test_mixed_priority_and_completed(self, weekdays_only_disabled):
        """Test priority sorting with completed tasks."""
        from datetime import date, timedelta

        today = date.today()
        yesterday = today - timedelta(days=1)

        tasks = [
            {
                "id": 1,
                "content": "Regular completed task",
                "created_at": f"{yesterday} 10:00:00",
                "completed_at": f"{yesterday} 11:00:00",
                "labels": [],
                "source": "cli",
            },
            {
                "id": 2,
                "content": "Important open task",
                "created_at": f"{yesterday} 09:00:00",
                "completed_at": None,
                "labels": ["i"],
                "source": "cli",
            },
        ]

        filtered = filter_tasks_by_date_range(tasks, days=1, weekdays_only=False)

        # Important task should come first, then completed task
        assert len(filtered) == 2
        assert filtered[0]["id"] == 2  # Important task first
        assert filtered[1]["id"] == 1  # Completed task second


class TestGetEditor:
    """Test the get_editor function."""

    @patch.dict(os.environ, {"EDITOR": "custom-editor"})
    def test_get_editor_from_env(self):
        """Test getting editor from environment variable."""
        editor = get_editor()
        assert editor == "custom-editor"

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    def test_get_editor_fallback(self, mock_run):
        """Test editor fallback behavior."""
        # Mock that nano is available
        mock_run.return_value.returncode = 0

        editor = get_editor()
        assert editor == "nano"
