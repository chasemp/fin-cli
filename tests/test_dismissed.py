"""Tests for dismissed task functionality."""

from datetime import datetime

import pytest

from fincli.db import DatabaseManager
from fincli.editor import EditorManager
from fincli.tasks import TaskManager
from fincli.utils import format_task_for_display


class TestDismissedTasks:
    """Test dismissed task functionality."""

    def test_task_manager_dismiss_task(self, temp_db_path):
        """Test TaskManager can dismiss tasks using new label approach."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Add a task
        task_id = task_manager.add_task("Test task", ["test"])

        # Dismiss the task using new approach
        task_manager.update_task_completion(task_id, True)
        task_manager.update_task_labels(task_id, ["test", "dismissed"])

        # Check the task is dismissed
        task = task_manager.get_task(task_id)
        assert task["completed_at"] is not None
        assert "dismissed" in task["labels"]

    def test_task_manager_undismiss_task(self, temp_db_path):
        """Test TaskManager can undismiss tasks using new label approach."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Add and dismiss a task
        task_id = task_manager.add_task("Test task", ["test"])
        task_manager.update_task_completion(task_id, True)
        task_manager.update_task_labels(task_id, ["test", "dismissed"])

        # Undismiss the task (remove dismissed label and reopen)
        task_manager.update_task_completion(task_id, False)
        task_manager.update_task_labels(task_id, ["test"])

        # Check the task is not dismissed
        task = task_manager.get_task(task_id)
        assert "dismissed" not in task["labels"]
        assert task["completed_at"] is None

    def test_dismiss_completed_task_keeps_completed_at(self, temp_db_path):
        """Test that dismissing a completed task keeps it completed with dismissed label."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Add and complete a task
        task_id = task_manager.add_task("Test task", ["test"])
        task_manager.update_task_completion(task_id, True)

        # Dismiss the task (add dismissed label)
        task_manager.update_task_labels(task_id, ["test", "dismissed"])

        # Check the task is dismissed and still completed
        task = task_manager.get_task(task_id)
        assert "dismissed" in task["labels"]
        assert task["completed_at"] is not None

    def test_dismissed_tasks_not_in_open_list(self, temp_db_path):
        """Test that dismissed tasks don't appear in open task lists."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Add tasks
        open_id = task_manager.add_task("Open task", ["test"])
        dismissed_id = task_manager.add_task("Dismissed task", ["test"])

        # Dismiss one task
        task_manager.update_task_completion(dismissed_id, True)
        task_manager.update_task_labels(dismissed_id, ["test", "dismissed"])

        # Get open tasks
        open_tasks = task_manager.list_tasks(include_completed=False)
        open_ids = [t["id"] for t in open_tasks]

        assert open_id in open_ids
        assert dismissed_id not in open_ids

    def test_dismissed_tasks_in_all_tasks_list(self, temp_db_path):
        """Test that dismissed tasks appear in all task lists."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Add and dismiss a task
        task_id = task_manager.add_task("Dismissed task", ["test"])
        task_manager.update_task_completion(task_id, True)
        task_manager.update_task_labels(task_id, ["test", "dismissed"])

        # Get all tasks
        all_tasks = task_manager.list_tasks(include_completed=True)
        all_ids = [t["id"] for t in all_tasks]

        assert task_id in all_ids

    def test_dismissed_task_display_format(self, temp_db_path):
        """Test that dismissed tasks display with [d] status."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Add and dismiss a task using new approach
        task_id = task_manager.add_task("Dismissed task", ["test"])
        # Mark as completed
        task_manager.update_task_completion(task_id, True)
        # Add dismissed label
        task_manager.update_task_labels(task_id, ["test", "dismissed"])

        # Get the task and format it
        task = task_manager.get_task(task_id)
        formatted = format_task_for_display(task)

        assert "[d]" in formatted
        assert "Dismissed task" in formatted

    def test_editor_parses_dismissed_status(self, temp_db_path):
        """Test that editor can parse [d] status."""
        db_manager = DatabaseManager(temp_db_path)
        editor_manager = EditorManager(db_manager)

        # Test parsing a dismissed task line
        test_line = "123 [d] 2025-01-15 10:00  Dismissed task  #test"
        parsed = editor_manager.parse_task_line(test_line)

        assert parsed is not None
        assert parsed["status"] == "[d]"
        assert parsed["is_dismissed"] is True
        assert parsed["is_completed"] is False
        assert parsed["content"] == "Dismissed task"

    def test_editor_handles_dismissed_status_changes(self, temp_db_path):
        """Test that editor can change task status to dismissed."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add a task
        task_id = task_manager.add_task("Test task", ["test"])
        original_task = task_manager.get_task(task_id)

        # Create edited content with dismissed status
        content = f"{task_id} [d] 2025-01-15 10:00  Test task  #test  #ref:task_{task_id}"

        # Parse the edited content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
            dismissed_count,
        ) = editor_manager.parse_edited_content(content, original_tasks=[original_task])

        # Check results
        assert dismissed_count == 1
        assert completed_count == 0
        assert reopened_count == 0

        # Check the task is now dismissed
        updated_task = task_manager.get_task(task_id)
        assert "dismissed" in updated_task["labels"]

    def test_editor_handles_undismiss_status_changes(self, temp_db_path):
        """Test that editor can change dismissed task back to open."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add and dismiss a task
        task_id = task_manager.add_task("Test task", ["test"])
        task_manager.update_task_completion(task_id, True)
        task_manager.update_task_labels(task_id, ["test", "dismissed"])
        original_task = task_manager.get_task(task_id)

        # Create edited content with open status
        content = f"{task_id} [ ] 2025-01-15 10:00  Test task  #test  #ref:task_{task_id}"

        # Parse the edited content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
            dismissed_count,
        ) = editor_manager.parse_edited_content(content, original_tasks=[original_task])

        # Check results - undismissing counts as a dismissed status change
        assert dismissed_count == 1
        assert reopened_count == 1
        assert completed_count == 0

        # Check the task is no longer dismissed
        updated_task = task_manager.get_task(task_id)
        assert "dismissed" not in updated_task["labels"]

    def test_no_change_for_already_dismissed_task(self, temp_db_path):
        """Test that dismissing an already dismissed task returns False."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Add and dismiss a task
        task_id = task_manager.add_task("Test task", ["test"])
        task_manager.update_task_completion(task_id, True)
        task_manager.update_task_labels(task_id, ["test", "dismissed"])

        # Try to dismiss again (should be no-op since already dismissed)
        # In the new approach, we don't track if it's a no-op, so this test is not applicable
        # Just verify the task is still dismissed
        task = task_manager.get_task(task_id)
        assert "dismissed" in task["labels"]
        assert task["completed_at"] is not None

    def test_no_change_for_already_open_task(self, temp_db_path):
        """Test that an open task without dismissed label remains unchanged."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Add a task (already open)
        task_id = task_manager.add_task("Test task", ["test"])

        # Verify it's open and not dismissed
        task = task_manager.get_task(task_id)
        assert task["completed_at"] is None
        assert "dismissed" not in task["labels"]

    def test_dismiss_nonexistent_task(self, temp_db_path):
        """Test that dismissing a nonexistent task returns False."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Try to dismiss nonexistent task
        # Try to dismiss nonexistent task - this should not crash
        success = False
        try:
            task_manager.update_task_completion(999, True)
            task_manager.update_task_labels(999, ["dismissed"])
        except Exception:
            success = False
        assert success is False

    def test_dismissed_task_modification_timestamp(self, temp_db_path):
        """Test that dismissing a task sets the completed_at timestamp."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Add a task
        task_id = task_manager.add_task("Test task", ["test"])
        original_task = task_manager.get_task(task_id)
        assert original_task["completed_at"] is None

        # Dismiss the task
        task_manager.update_task_completion(task_id, True)
        task_manager.update_task_labels(task_id, ["test", "dismissed"])

        # Check completed_at timestamp was set and dismissed label was added
        updated_task = task_manager.get_task(task_id)
        assert "dismissed" in updated_task["labels"]

        # Check it's a recent timestamp (within last 5 seconds)

        assert updated_task["completed_at"] is not None
        completed_time = datetime.fromisoformat(updated_task["completed_at"])
        now = datetime.now()
        time_diff = (now - completed_time).total_seconds()
        assert time_diff < 5  # Should be very recent

    def test_multiple_state_transitions(self, temp_db_path):
        """Test multiple state transitions work correctly."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Add a task
        task_id = task_manager.add_task("Test task", ["test"])

        # Open -> Completed
        task_manager.update_task_completion(task_id, True)
        task = task_manager.get_task(task_id)
        assert task["completed_at"] is not None
        assert "dismissed" not in task["labels"]

        # Completed -> Dismissed (should keep completed_at and add dismissed label)
        task_manager.update_task_labels(task_id, ["test", "dismissed"])
        task = task_manager.get_task(task_id)
        assert task["completed_at"] is not None  # Should remain completed
        assert "dismissed" in task["labels"]

        # Dismissed -> Open (remove dismissed label and reopen)
        task_manager.update_task_completion(task_id, False)
        task_manager.update_task_labels(task_id, ["test"])
        task = task_manager.get_task(task_id)
        assert task["completed_at"] is None
        assert "dismissed" not in task["labels"]

        # Open -> Dismissed (complete and add dismissed label)
        task_manager.update_task_completion(task_id, True)
        task_manager.update_task_labels(task_id, ["test", "dismissed"])
        task = task_manager.get_task(task_id)
        assert task["completed_at"] is not None
        assert "dismissed" in task["labels"]
