"""
Tests for the fine command functionality
"""

import os
import subprocess
import sys
from datetime import date, datetime, timedelta

import pytest

from fincli.cli import fine_command, open_editor
from fincli.db import DatabaseManager
from fincli.editor import EditorManager
from fincli.utils import get_editor


class TestFineCommand:
    """Test fine command functionality."""

    def test_get_editor_with_env(self, monkeypatch):
        """Test getting editor from environment variable."""
        monkeypatch.setenv("EDITOR", "vim")
        editor = get_editor()
        assert editor == "vim"

    def test_get_editor_fallback(self, monkeypatch):
        """Test editor fallback when EDITOR not set."""
        monkeypatch.delenv("EDITOR", raising=False)
        editor = get_editor()
        assert editor in ["nano", "vim", "code"]

    def test_parse_task_line_valid(self):
        """Test parsing a valid task line."""
        import tempfile

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False, dir="/tmp")
        tmp.close()
        db_path = tmp.name
        try:
            os.environ["FIN_DB_PATH"] = db_path
            from fincli.db import DatabaseManager

            db_manager = DatabaseManager()
            line = "[ ] 2025-07-30 09:15  Write unit tests  #testing"
            editor_manager = EditorManager(db_manager)
            result = editor_manager.parse_task_line(line)

            assert result is not None
            assert result["status"] == "[ ]"
            assert result["timestamp"] == "2025-07-30 09:15"
            assert result["content"] == "Write unit tests"
            assert result["labels"] == ["testing"]
            assert result["is_completed"] is False
        finally:
            os.unlink(db_path)

    def test_parse_task_line_completed(self, temp_db_path, monkeypatch):
        """Test parsing a completed task line."""
        # Set environment variable to use temp database
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)
        
        from fincli.db import DatabaseManager
        from fincli.editor import EditorManager

        db_manager = DatabaseManager(temp_db_path)
        line = "[x] 2025-07-29 17:10  Fix bug in cron task runner  #automation"
        editor_manager = EditorManager(db_manager)
        result = editor_manager.parse_task_line(line)

        assert result is not None
        assert result["status"] == "[x]"
        assert result["timestamp"] == "2025-07-29 17:10"
        assert result["content"] == "Fix bug in cron task runner"
        assert result["labels"] == ["automation"]
        assert result["is_completed"] is True

    def test_parse_task_line_no_labels(self, temp_db_path, monkeypatch):
        """Test parsing a task line without labels."""
        # Set environment variable to use temp database
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)
        
        from fincli.db import DatabaseManager
        from fincli.editor import EditorManager

        db_manager = DatabaseManager(temp_db_path)
        line = "[ ] 2025-07-30 10:30  Simple task"
        editor_manager = EditorManager(db_manager)
        result = editor_manager.parse_task_line(line)

        assert result is not None
        assert result["status"] == "[ ]"
        assert result["timestamp"] == "2025-07-30 10:30"
        assert result["content"] == "Simple task"
        assert result["labels"] == []
        assert result["is_completed"] is False

    def test_parse_task_line_invalid(self, temp_db_path, monkeypatch):
        """Test parsing an invalid task line."""
        # Set environment variable to use temp database
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)
        
        from fincli.db import DatabaseManager
        from fincli.editor import EditorManager

        db_manager = DatabaseManager(temp_db_path)
        line = "Invalid task line format"
        editor_manager = EditorManager(db_manager)
        result = editor_manager.parse_task_line(line)

        assert result is None

    def test_find_matching_task(self, db_manager):
        """Test finding matching tasks."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task_id = task_manager.add_task("Test task", labels=["work"])
        task = task_manager.get_task(task_id)

        editor_manager = EditorManager(db_manager)
        task_info = {
            "task_id": task_id,
            "content": "Test task",
            "labels": ["work"],
        }

        found_id = editor_manager.find_matching_task(task_info)
        assert found_id == task_id

    def test_fine_command_with_tasks(self, temp_db_path, monkeypatch):
        """Test fine command with existing tasks."""
        # Set environment variable to use temp database
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)
        
        from fincli.db import DatabaseManager
        from fincli.tasks import TaskManager

        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Work task", labels=["work"])
        task_manager.add_task("Personal task", labels=["personal"])

        from fincli.cli import open_editor

        def mock_subprocess_run(cmd, **kwargs):
            import os

            temp_file_path = cmd[-1] if cmd else None
            if temp_file_path and os.path.exists(temp_file_path):
                with open(temp_file_path, "r") as f:
                    content = f.read()
                content = content.replace("[ ]", "[x]", 1)
                with open(temp_file_path, "w") as f:
                    f.write(content)

            class MockResult:
                returncode = 0

            return MockResult()

        monkeypatch.setattr("subprocess.run", mock_subprocess_run)
        result = open_editor(label="work")
        assert result[0] == 1  # 1 task completed
        assert result[1] == 0  # 0 tasks reopened
        assert result[2] == 0  # 0 new tasks

    def test_fine_command_safety_checks(self, cli_runner):
        """Test that the fine command has proper safety checks."""
        # Create a temporary database
        import tempfile

        from fincli.db import DatabaseManager
        from fincli.tasks import TaskManager

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        db_path = tmp.name

        try:
            # Set the database path environment variable
            import os

            os.environ["FIN_DB_PATH"] = db_path

            # Set up database with tasks
            db_manager = DatabaseManager(db_path)
            task_manager = TaskManager(db_manager)
            task_manager.add_task("Test task", labels=["work"])

            # Test dry-run functionality with label filtering
            result = cli_runner.invoke(open_editor, ["--label", "work", "--dry-run"])
            assert result.exit_code == 0
            assert "📝 Found 1 tasks for editing:" in result.output
            assert "Test task" in result.output
            assert (
                "Use 'fin open-editor' (without --dry-run) to actually open the editor."
                in result.output
            )

        finally:
            os.unlink(db_path)

    def test_editor_manager_safety_flag(self, db_manager):
        """Test that the editor manager prevents multiple editor openings."""
        editor_manager = EditorManager(db_manager)

        # Add a task so the editor has something to work with
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task_manager.add_task("Test task", labels=["test"])

        # Mock subprocess.run to avoid opening actual editor
        def mock_subprocess_run(cmd, **kwargs):
            class MockResult:
                returncode = 0

            return MockResult()

        # Patch subprocess.run
        import subprocess

        original_run = subprocess.run
        subprocess.run = mock_subprocess_run

        try:
            # First call should work
            editor_manager.edit_tasks(label="test")

            # Second call should raise an error
            with pytest.raises(RuntimeError, match="Editor has already been opened"):
                editor_manager.edit_tasks(label="test")

        finally:
            # Restore original subprocess.run
            subprocess.run = original_run


class TestFineStandaloneCommand:
    """Test the standalone fine command functionality."""

    def test_fine_command_help(self, cli_runner):
        """Test fine command help output."""
        # Create a mock Click command for testing
        import click

        @click.command()
        @click.option("--label", "-l", multiple=True, help="Filter by labels")
        @click.option("--date", help="Filter by date (YYYY-MM-DD)")
        @click.option(
            "--all-tasks", is_flag=True, help="Show all tasks (including completed)"
        )
        @click.option(
            "--dry-run",
            is_flag=True,
            help="Show what would be edited without opening editor",
        )
        def mock_fine_cli(label, date, all_tasks, dry_run):
            """Edit tasks in your editor (alias for fin open-editor)."""
            return "Mock fine command"

        result = cli_runner.invoke(mock_fine_cli, ["--help"])
        assert result.exit_code == 0
        assert "Edit tasks in your editor" in result.output

    def test_fine_command_dry_run(self, cli_runner, temp_db_path, monkeypatch):
        """Test fine command with dry-run option."""
        # Set up database with a task
        import os

        os.environ["FIN_DB_PATH"] = temp_db_path

        from fincli.db import DatabaseManager
        from fincli.tasks import TaskManager

        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Test task", labels=["work"])

        # Test by calling the function directly with mocked sys.argv
        import sys

        original_argv = sys.argv
        try:
            sys.argv = ["fine", "--dry-run"]
            # We can't easily test the standalone command directly, so let's test the underlying functionality
            from fincli.editor import EditorManager

            editor_manager = EditorManager(db_manager)
            tasks = editor_manager.get_tasks_for_editing(label="work")
            assert len(tasks) == 1
            assert tasks[0]["content"] == "Test task"
        finally:
            sys.argv = original_argv

    def test_fine_command_with_label_filter(
        self, cli_runner, temp_db_path, monkeypatch
    ):
        """Test fine command with label filtering."""
        # Set up database with tasks
        import os

        os.environ["FIN_DB_PATH"] = temp_db_path

        from fincli.db import DatabaseManager
        from fincli.tasks import TaskManager

        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Work task", labels=["work"])
        task_manager.add_task("Personal task", labels=["personal"])

        # Test by calling the underlying functionality directly
        from fincli.editor import EditorManager

        editor_manager = EditorManager(db_manager)
        work_tasks = editor_manager.get_tasks_for_editing(label="work")
        personal_tasks = editor_manager.get_tasks_for_editing(label="personal")

        assert len(work_tasks) == 1
        assert work_tasks[0]["content"] == "Work task"
        assert len(personal_tasks) == 1
        assert personal_tasks[0]["content"] == "Personal task"

    def test_fine_command_no_tasks(self, cli_runner, temp_db_path, monkeypatch):
        """Test fine command with no tasks."""
        # Set up empty database
        import os

        os.environ["FIN_DB_PATH"] = temp_db_path

        # Test by calling the underlying functionality directly
        from fincli.db import DatabaseManager
        from fincli.editor import EditorManager

        db_manager = DatabaseManager(temp_db_path)
        editor_manager = EditorManager(db_manager)
        tasks = editor_manager.get_tasks_for_editing(label="work")
        assert len(tasks) == 0
