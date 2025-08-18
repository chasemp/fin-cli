"""
Tests for due date functionality in FinCLI

Tests database schema, date parsing, CLI integration, and display formatting.
"""

import pytest
from datetime import date, datetime

from fincli.db import DatabaseManager
from fincli.tasks import TaskManager
from fincli.utils import DateParser, format_task_for_display


class TestDateParser:
    """Test the DateParser utility class."""

    def test_parse_due_date_yyyy_mm_dd(self):
        """Test parsing YYYY-MM-DD format."""
        result = DateParser.parse_due_date("2025-06-17")
        assert result == "2025-06-17"

    def test_parse_due_date_mm_dd(self):
        """Test parsing MM/DD format (assumes current year)."""
        result = DateParser.parse_due_date("06/17")
        # June 17th has passed this year, so it should use next year
        assert result == "2026-06-17"

    def test_parse_due_date_mm_dd_yyyy(self):
        """Test parsing MM/DD/YYYY format."""
        result = DateParser.parse_due_date("06/17/2025")
        assert result == "2025-06-17"

    def test_parse_due_date_mm_dd_format(self):
        """Test parsing MM-DD format (assumes current year)."""
        result = DateParser.parse_due_date("06-17")
        # June 17th has passed this year, so it should use next year
        assert result == "2026-06-17"

    def test_parse_due_date_invalid_format(self):
        """Test parsing invalid date formats."""
        assert DateParser.parse_due_date("invalid") is None
        assert DateParser.parse_due_date("25/13/2025") is None  # Invalid month
        assert DateParser.parse_due_date("06/32/2025") is None  # Invalid day

    def test_parse_due_date_empty(self):
        """Test parsing empty or None dates."""
        assert DateParser.parse_due_date("") is None
        assert DateParser.parse_due_date(None) is None
        assert DateParser.parse_due_date("   ") is None

    def test_validate_due_date(self):
        """Test due date validation."""
        assert DateParser.validate_due_date("2025-06-17") is True
        assert DateParser.validate_due_date("2025-02-29") is False  # 2025 is not a leap year
        assert DateParser.validate_due_date("2024-02-29") is True   # 2024 is a leap year
        assert DateParser.validate_due_date("invalid") is False
        assert DateParser.validate_due_date("2025-13-01") is False  # Invalid month

    def test_is_overdue(self):
        """Test overdue date detection."""
        from datetime import timedelta
        
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        assert DateParser.is_overdue(yesterday) is True
        assert DateParser.is_overdue(tomorrow) is False

    def test_is_due_soon(self):
        """Test due soon detection."""
        from datetime import timedelta
        
        today = date.today().strftime("%Y-%m-%d")
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        next_week = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        assert DateParser.is_due_soon(today, days=3) is True
        assert DateParser.is_due_soon(tomorrow, days=3) is True
        assert DateParser.is_due_soon(next_week, days=3) is False


class TestDatabaseSchema:
    """Test database schema for due dates."""

    def test_database_has_due_date_column(self, temp_db_path):
        """Test that database has due_date column."""
        db_manager = DatabaseManager(temp_db_path)
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [column[1] for column in cursor.fetchall()]
            
            assert "due_date" in columns

    def test_due_date_column_type(self, temp_db_path):
        """Test that due_date column is TEXT type."""
        db_manager = DatabaseManager(temp_db_path)
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(tasks)")
            columns = {column[1]: column[2] for column in cursor.fetchall()}
            
            assert columns["due_date"] == "TEXT"

    def test_due_date_index_exists(self, temp_db_path):
        """Test that due_date index exists."""
        db_manager = DatabaseManager(temp_db_path)
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA index_list(tasks)")
            indexes = [index[1] for index in cursor.fetchall()]
            
            assert "idx_tasks_due_date" in indexes


class TestTaskManagerDueDates:
    """Test TaskManager due date functionality."""

    def test_add_task_with_due_date(self, temp_db_path):
        """Test adding a task with a due date."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        
        task_id = task_manager.add_task(
            "Test task with due date",
            labels=["test"],
            due_date="2025-06-17"
        )
        
        assert task_id == 1
        
        # Verify task was added with due date
        task = task_manager.get_task(task_id)
        assert task["due_date"] == "2025-06-17"
        assert task["content"] == "Test task with due date"

    def test_add_task_without_due_date(self, temp_db_path):
        """Test adding a task without a due date."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        
        task_id = task_manager.add_task("Test task without due date")
        
        assert task_id == 1
        
        # Verify task was added without due date
        task = task_manager.get_task(task_id)
        assert task["due_date"] is None

    def test_update_task_due_date(self, temp_db_path):
        """Test updating a task's due date."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        
        # Add task without due date
        task_id = task_manager.add_task("Test task")
        
        # Update due date
        result = task_manager.update_task_due_date(task_id, "2025-06-17")
        assert result is True
        
        # Verify due date was updated
        task = task_manager.get_task(task_id)
        assert task["due_date"] == "2025-06-17"

    def test_update_task_due_date_no_change(self, temp_db_path):
        """Test updating due date when no change is needed."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        
        # Add task with due date
        task_id = task_manager.add_task(
            "Test task",
            due_date="2025-06-17"
        )
        
        # Try to update with same due date
        result = task_manager.update_task_due_date(task_id, "2025-06-17")
        assert result is False  # No change needed

    def test_update_task_due_date_remove(self, temp_db_path):
        """Test removing a task's due date."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        
        # Add task with due date
        task_id = task_manager.add_task(
            "Test task",
            due_date="2025-06-17"
        )
        
        # Remove due date
        result = task_manager.update_task_due_date(task_id, None)
        assert result is True
        
        # Verify due date was removed
        task = task_manager.get_task(task_id)
        assert task["due_date"] is None

    def test_list_tasks_includes_due_date(self, temp_db_path):
        """Test that list_tasks includes due_date field."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        
        # Add tasks with and without due dates
        task_manager.add_task("Task 1", due_date="2025-06-17")
        task_manager.add_task("Task 2")
        
        tasks = task_manager.list_tasks()
        
        assert len(tasks) == 2
        assert tasks[0]["due_date"] == "2025-06-17"
        assert tasks[1]["due_date"] is None


class TestDisplayFormatting:
    """Test due date display formatting."""

    def test_format_task_for_display_with_due_date(self, temp_db_path):
        """Test that tasks with due dates show due date at end."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        
        task_id = task_manager.add_task(
            "Test task with due date",
            labels=["test"],
            due_date="2025-06-17"
        )
        
        task = task_manager.get_task(task_id)
        formatted = format_task_for_display(task)
        
        # Due date should appear at end of line
        assert formatted.endswith("due:2025-06-17")
        assert "Test task with due date" in formatted

    def test_format_task_for_display_without_due_date(self, temp_db_path):
        """Test that tasks without due dates don't show due date."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        
        task_id = task_manager.add_task("Test task without due date")
        
        task = task_manager.get_task(task_id)
        formatted = format_task_for_display(task)
        
        # Should not contain due date
        assert "due:" not in formatted
        assert "Test task without due date" in formatted

    def test_format_task_for_display_with_labels_and_due_date(self, temp_db_path):
        """Test that tasks with both labels and due dates format correctly."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        
        task_id = task_manager.add_task(
            "Test task",
            labels=["work", "urgent"],
            due_date="2025-06-17"
        )
        
        task = task_manager.get_task(task_id)
        formatted = format_task_for_display(task)
        
        # Should have labels and due date at end
        assert "#work" in formatted
        assert "#urgent" in formatted
        assert formatted.endswith("due:2025-06-17")


class TestCLIIntegration:
    """Test CLI integration with due dates."""

    def test_cli_add_task_with_due_date(self, temp_db_path, monkeypatch):
        """Test CLI command adds task with due date."""
        from fincli.cli import add_task
        
        # Mock the database path
        monkeypatch.setenv("FIN_DB_PATH", str(temp_db_path))
        
        # Add task with due date
        add_task("Test CLI task", ("test",), "cli", "2025-06-17")
        
        # Verify task was added
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        
        tasks = task_manager.list_tasks()
        assert len(tasks) == 1
        assert tasks[0]["due_date"] == "2025-06-17"
        assert tasks[0]["content"] == "Test CLI task"


class TestEditorIntegration:
    """Test editor integration with due dates."""

    def test_editor_creates_edit_file_with_due_dates(self, temp_db_path):
        """Test that editor creates edit file content with due dates."""
        from fincli.editor import EditorManager
        
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)
        
        # Add a task with due date
        task_id = task_manager.add_task(
            "Test task with due date",
            labels=["test"],
            due_date="2025-06-17"
        )
        
        # Get tasks for editing
        tasks = editor_manager.get_tasks_for_editing()
        
        # Create edit file content
        content = editor_manager.create_edit_file_content(tasks)
        
        # Check that due date appears in the content
        assert "due:2025-06-17" in content
        assert "Test task with due date" in content

    def test_editor_parses_due_date_changes(self, temp_db_path):
        """Test that editor can parse due date changes."""
        from fincli.editor import EditorManager
        
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)
        
        # Add a task with due date
        task_id = task_manager.add_task(
            "Test task",
            due_date="2025-06-17"
        )
        
        # Get original task
        original_task = task_manager.get_task(task_id)
        
        # Create edit file content
        tasks = editor_manager.get_tasks_for_editing()
        original_content = editor_manager.create_edit_file_content(tasks)
        
        # Modify the due date in the content
        modified_lines = []
        for line in original_content.splitlines():
            if "Test task" in line:
                # Change the due date
                line = line.replace("due:2025-06-17", "due:2025-07-15")
            modified_lines.append(line)
        
        modified_content = "\n".join(modified_lines)
        
        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content, original_tasks=[original_task])
        
        # Should detect due date change
        assert content_modified_count == 1
        
        # Verify due date was updated
        updated_task = task_manager.get_task(task_id)
        assert updated_task["due_date"] == "2025-07-15"

    def test_editor_parses_due_date_removal(self, temp_db_path):
        """Test that editor can parse due date removal."""
        from fincli.editor import EditorManager
        
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)
        
        # Add a task with due date
        task_id = task_manager.add_task(
            "Test task",
            due_date="2025-06-17"
        )
        
        # Get original task
        original_task = task_manager.get_task(task_id)
        
        # Create edit file content
        tasks = editor_manager.get_tasks_for_editing()
        original_content = editor_manager.create_edit_file_content(tasks)
        
        # Remove the due date from the content
        modified_lines = []
        for line in original_content.splitlines():
            if "Test task" in line:
                # Remove the due date
                line = line.replace("  due:2025-06-17", "")
            modified_lines.append(line)
        
        modified_content = "\n".join(modified_lines)
        
        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content, original_tasks=[original_task])
        
        # Should detect due date change
        assert content_modified_count == 1
        
        # Verify due date was removed
        updated_task = task_manager.get_task(task_id)
        assert updated_task["due_date"] is None

    def test_editor_parses_new_task_with_due_date(self, temp_db_path):
        """Test that editor can parse new tasks with due dates."""
        from fincli.editor import EditorManager
        
        db_manager = DatabaseManager(temp_db_path)
        editor_manager = EditorManager(db_manager)
        
        # Create edit file content with a new task line (no task ID, no timestamp)
        new_task_line = "[ ] New task with due date  #test  due:2025-09-15"
        
        # Parse the content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(new_task_line)
        
        # Should create new task
        assert new_tasks_count == 1
        
        # Verify task was created with due date
        task_manager = TaskManager(db_manager)
        tasks = task_manager.list_tasks()
        assert len(tasks) == 1
        assert tasks[0]["content"] == "New task with due date"
        assert tasks[0]["due_date"] == "2025-09-15"
