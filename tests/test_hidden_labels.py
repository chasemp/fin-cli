"""
Tests for the hidden labels functionality.

Tests the hidden labels system that filters out metadata labels by default
and only shows them with verbose mode.
"""

from unittest.mock import Mock

import pytest

from fincli.utils import (
    HIDDEN_LABELS,
    filter_hidden_labels,
    format_task_for_display,
    get_hidden_labels_info,
)


class TestHiddenLabelsConfiguration:
    """Test the hidden labels configuration."""

    def test_hidden_labels_contains_expected_labels(self):
        """Test that HIDDEN_LABELS contains all expected metadata labels."""
        expected_labels = {
            "authority:full",
            "authority:status",
            "source:slack",
            "source:gmail",
            "source:confluence",
            "source:sheets",
            "remote",
            "mod:*",
        }

        assert set(HIDDEN_LABELS.keys()) == expected_labels

    def test_hidden_labels_have_descriptions(self):
        """Test that all hidden labels have meaningful descriptions."""
        for label, description in HIDDEN_LABELS.items():
            assert description is not None
            assert len(description) > 0
            assert isinstance(description, str)

    def test_mod_wildcard_pattern_exists(self):
        """Test that the mod:* wildcard pattern exists for modification timestamps."""
        assert "mod:*" in HIDDEN_LABELS
        assert "mod:8/28" not in HIDDEN_LABELS  # Specific mod labels shouldn't be in config


class TestFilterHiddenLabels:
    """Test the filter_hidden_labels function."""

    def test_filter_hidden_labels_no_labels(self):
        """Test filtering with no labels."""
        result = filter_hidden_labels([], verbose=False)
        assert result == []

    def test_filter_hidden_labels_no_hidden_labels(self):
        """Test filtering with no hidden labels."""
        labels = ["work", "urgent", "project"]
        result = filter_hidden_labels(labels, verbose=False)
        assert result == labels

    def test_filter_hidden_labels_hide_metadata_labels(self):
        """Test that metadata labels are hidden by default."""
        labels = ["work", "authority:full", "source:slack", "urgent"]
        result = filter_hidden_labels(labels, verbose=False)
        assert result == ["work", "urgent"]
        assert "authority:full" not in result
        assert "source:slack" not in result

    def test_filter_hidden_labels_show_all_with_verbose(self):
        """Test that all labels are shown with verbose mode."""
        labels = ["work", "authority:full", "source:slack", "urgent"]
        result = filter_hidden_labels(labels, verbose=True)
        assert result == labels
        assert "authority:full" in result
        assert "source:slack" in result

    def test_filter_hidden_labels_wildcard_patterns(self):
        """Test that wildcard patterns like mod:* work correctly."""
        labels = ["work", "mod:8/28", "mod:8/29", "urgent"]
        result = filter_hidden_labels(labels, verbose=False)
        assert result == ["work", "urgent"]
        assert "mod:8/28" not in result
        assert "mod:8/29" not in result

    def test_filter_hidden_labels_wildcard_patterns_verbose(self):
        """Test that wildcard patterns are shown with verbose mode."""
        labels = ["work", "mod:8/28", "mod:8/29", "urgent"]
        result = filter_hidden_labels(labels, verbose=True)
        assert result == labels
        assert "mod:8/28" in result
        assert "mod:8/29" in result

    def test_filter_hidden_labels_mixed_patterns(self):
        """Test filtering with a mix of regular and hidden labels."""
        labels = ["work", "authority:full", "mod:8/28", "urgent", "source:slack", "project"]
        result = filter_hidden_labels(labels, verbose=False)
        assert result == ["work", "urgent", "project"]
        assert "authority:full" not in result
        assert "mod:8/28" not in result
        assert "source:slack" not in result

    def test_filter_hidden_labels_case_sensitive(self):
        """Test that label filtering is case sensitive."""
        labels = ["Work", "AUTHORITY:FULL", "source:SLACK"]
        result = filter_hidden_labels(labels, verbose=False)
        assert result == ["Work", "AUTHORITY:FULL", "source:SLACK"]  # All should remain


class TestGetHiddenLabelsInfo:
    """Test the get_hidden_labels_info function."""

    def test_get_hidden_labels_info_returns_copy(self):
        """Test that get_hidden_labels_info returns a copy, not the original."""
        info1 = get_hidden_labels_info()
        info2 = get_hidden_labels_info()

        # Should be equal
        assert info1 == info2

        # But should be different objects (copies)
        assert info1 is not info2

    def test_get_hidden_labels_info_contains_all_labels(self):
        """Test that get_hidden_labels_info returns all hidden labels."""
        info = get_hidden_labels_info()
        assert set(info.keys()) == set(HIDDEN_LABELS.keys())

    def test_get_hidden_labels_info_descriptions_match(self):
        """Test that descriptions in get_hidden_labels_info match HIDDEN_LABELS."""
        info = get_hidden_labels_info()
        for label in HIDDEN_LABELS:
            assert info[label] == HIDDEN_LABELS[label]


class TestFormatTaskForDisplayWithHiddenLabels:
    """Test that format_task_for_display properly handles hidden labels."""

    def test_format_task_for_display_hides_labels_by_default(self):
        """Test that hidden labels are filtered out by default."""
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-28T10:00:00",
            "completed_at": None,
            "labels": ["work", "authority:full", "source:slack"],
            "modified_at": None,
        }

        result = format_task_for_display(task, verbose=False)

        # Should contain work label
        assert "#work" in result

        # Should NOT contain hidden labels
        assert "#authority:full" not in result
        assert "#source:slack" not in result

    def test_format_task_for_display_shows_all_labels_with_verbose(self):
        """Test that all labels are shown with verbose mode."""
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-28T10:00:00",
            "completed_at": None,
            "labels": ["work", "authority:full", "source:slack"],
            "modified_at": None,
        }

        result = format_task_for_display(task, verbose=True)

        # Should contain all labels
        assert "#work" in result
        assert "#authority:full" in result
        assert "#source:slack" in result

    def test_format_task_for_display_no_labels(self):
        """Test that tasks without labels display correctly."""
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-28T10:00:00",
            "completed_at": None,
            "labels": None,
            "modified_at": None,
        }

        result = format_task_for_display(task, verbose=False)
        assert "#work" not in result
        assert "#authority:full" not in result

    def test_format_task_for_display_empty_labels_list(self):
        """Test that tasks with empty labels list display correctly."""
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-28T10:00:00",
            "completed_at": None,
            "labels": [],
            "modified_at": None,
        }

        result = format_task_for_display(task, verbose=False)
        assert "#work" not in result
        assert "#authority:full" not in result


class TestModificationTimestampLabels:
    """Test the modification timestamp label functionality."""

    def test_modification_label_not_shown_by_default(self):
        """Test that modification labels are hidden by default."""
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-28T10:00:00",
            "completed_at": None,
            "labels": ["work"],
            "modified_at": "2025-08-28T11:00:00",
        }

        result = format_task_for_display(task, verbose=False)

        # Should NOT contain modification label
        assert "#mod:8/28" not in result
        assert "mod:" not in result

    def test_modification_label_shown_with_verbose(self):
        """Test that modification labels are shown with verbose mode."""
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-28T10:00:00",
            "completed_at": None,
            "labels": ["work"],
            "modified_at": "2025-08-28T11:00:00",
        }

        result = format_task_for_display(task, verbose=True)

        # Should contain modification label
        assert "#mod:2025-08-28" in result

    def test_modification_label_format(self):
        """Test that modification labels use the correct format."""
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-28T10:00:00",
            "completed_at": None,
            "labels": ["work"],
            "modified_at": "2025-08-28T11:00:00",
        }

        result = format_task_for_display(task, verbose=True)

        # Should use #mod:YYYY-MM-DD format
        assert "#mod:2025-08-28" in result
        assert "(mod:" not in result  # Old format should not appear

    def test_modification_label_with_existing_labels(self):
        """Test that modification labels integrate with existing labels."""
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-28T10:00:00",
            "completed_at": None,
            "labels": ["work", "urgent"],
            "modified_at": "2025-08-28T11:00:00",
        }

        result = format_task_for_display(task, verbose=True)

        # Should contain all labels including modification
        assert "#work" in result
        assert "#urgent" in result
        assert "#mod:2025-08-28" in result

    def test_modification_label_no_modified_at(self):
        """Test that tasks without modified_at don't show modification label."""
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-28T10:00:00",
            "completed_at": None,
            "labels": ["work"],
            "modified_at": None,
        }

        result = format_task_for_display(task, verbose=True)

        # Should NOT contain modification label
        assert "#mod:" not in result

    def test_modification_label_completed_task(self):
        """Test modification labels for completed tasks."""
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-28T10:00:00",
            "completed_at": "2025-08-28T12:00:00",
            "labels": ["work"],
            "modified_at": "2025-08-28T13:00:00",  # Modified after completion
        }

        result = format_task_for_display(task, verbose=True)

        # Should contain modification label
        assert "#mod:2025-08-28" in result

    def test_modification_label_open_task(self):
        """Test modification labels for open tasks."""
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-28T10:00:00",
            "completed_at": None,
            "labels": ["work"],
            "modified_at": "2025-08-28T11:00:00",  # Modified after creation
        }

        result = format_task_for_display(task, verbose=True)

        # Should contain modification label
        assert "#mod:2025-08-28" in result


class TestHiddenLabelsIntegration:
    """Test integration of hidden labels with other systems."""

    def test_hidden_labels_with_task_manager(self, temp_db_path):
        """Test that hidden labels work correctly with TaskManager."""
        from fincli.db import DatabaseManager
        from fincli.tasks import TaskManager

        # Create a test database (automatically initialized)
        db_manager = DatabaseManager(temp_db_path)

        task_manager = TaskManager(db_manager)

        # Add a task with hidden labels
        task_id = task_manager.add_task("Test task with hidden labels", labels=["work", "authority:full", "source:slack"])

        # Get the task
        task = task_manager.get_task(task_id)
        assert task is not None

        # Verify labels are stored correctly
        assert "work" in task["labels"]
        assert "authority:full" in task["labels"]
        assert "source:slack" in task["labels"]

    def test_hidden_labels_filtering_consistency(self):
        """Test that hidden labels filtering is consistent across different functions."""
        labels = ["work", "authority:full", "source:slack", "urgent"]

        # Test filtering
        filtered = filter_hidden_labels(labels, verbose=False)
        assert filtered == ["work", "urgent"]

        # Test that the same filtering logic applies to format_task_for_display
        task = {
            "id": 1,
            "content": "Test task",
            "created_at": "2025-08-28T10:00:00",
            "completed_at": None,
            "labels": labels,
            "modified_at": None,
        }

        result = format_task_for_display(task, verbose=False)
        assert "#work" in result
        assert "#urgent" in result
        assert "#authority:full" not in result
        assert "#source:slack" not in result
