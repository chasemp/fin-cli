"""
Simplified tests for the fine command functionality without interactive editor.
"""

from datetime import date, timedelta

from fincli.db import DatabaseManager
from fincli.tasks import TaskManager


class TestFineCommandSimple:
    """Test fine command functionality without editor interaction."""

    def test_fine_command_no_tasks_empty_db(self, temp_db_path, monkeypatch):
        """Test fine command with no tasks in empty database."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        # Test that the command doesn't crash with empty database
        from click.testing import CliRunner

        from fincli.cli import open_editor

        runner = CliRunner()
        result = runner.invoke(open_editor, [])

        assert result.exit_code == 0
        assert "📝 No tasks found for editing." in result.output

    def test_fine_command_dry_run(self, temp_db_path, monkeypatch):
        """Test fine command with dry-run option."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        # Add tasks
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Work task", labels=["work"])
        task_manager.add_task("Personal task", labels=["personal"])

        # Test dry-run functionality
        from click.testing import CliRunner

        from fincli.cli import open_editor

        runner = CliRunner()
        result = runner.invoke(open_editor, ["--dry-run"])

        assert result.exit_code == 0
        assert "📝 Found 2 tasks for editing:" in result.output
        assert "Work task" in result.output
        assert "Personal task" in result.output
        assert (
            "Use 'fin open-editor' (without --dry-run) to actually open the editor."
            in result.output
        )

    def test_fine_command_task_filtering(self, temp_db_path, monkeypatch, test_dates):
        """Test fine command task filtering logic."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        # Add tasks
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Add a task for today
        task_manager.add_task("Today's task", labels=["work"])

        # Add a task for yesterday (mark as completed)
        yesterday_task_id = task_manager.add_task(
            "Yesterday's task", labels=["personal"]
        )
        import sqlite3

        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            # Use test_dates fixture for consistent dates
            yesterday = test_dates["yesterday"]
            cursor.execute(
                "UPDATE tasks SET completed_at = ? WHERE id = ?",
                (yesterday.strftime("%Y-%m-%d 12:00:00"), yesterday_task_id),
            )
            conn.commit()

        # Test that filtering works correctly
        from fincli.editor import EditorManager

        # Test label filtering
        editor_manager = EditorManager(db_manager)
        work_tasks = editor_manager.get_tasks_for_editing(label="work")
        assert len(work_tasks) == 1
        assert work_tasks[0]["content"] == "Today's task"

        # Test date filtering
        today_tasks = editor_manager.get_tasks_for_editing(
            target_date=test_dates["today"].strftime("%Y-%m-%d")
        )
        assert len(today_tasks) == 1
        assert today_tasks[0]["content"] == "Today's task"

    def test_fine_command_help(self):
        """Test fine command help output."""
        from click.testing import CliRunner

        from fincli.cli import open_editor

        runner = CliRunner()
        result = runner.invoke(open_editor, ["--help"])

        assert result.exit_code == 0
        assert (
            "Open tasks in your editor for editing completion status" in result.output
        )
        assert "--label" in result.output
        assert "--date" in result.output
        assert "--dry-run" in result.output

    def test_fine_command_label_filtering(self, temp_db_path, monkeypatch):
        """Test fine command with label filtering."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        # Add tasks with different labels
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Work task", labels=["work"])
        task_manager.add_task("Personal task", labels=["personal"])

        # Test the filtering logic directly
        from fincli.editor import EditorManager

        editor_manager = EditorManager(db_manager)
        work_tasks = editor_manager.get_tasks_for_editing(label="work")
        assert len(work_tasks) == 1
        assert work_tasks[0]["content"] == "Work task"

        personal_tasks = editor_manager.get_tasks_for_editing(label="personal")
        assert len(personal_tasks) == 1
        assert personal_tasks[0]["content"] == "Personal task"

        # Test non-existent label
        nonexistent_tasks = editor_manager.get_tasks_for_editing(label="nonexistent")
        assert len(nonexistent_tasks) == 0

    def test_fine_command_with_dry_run_and_label(self, temp_db_path, monkeypatch):
        """Test fine command with dry-run and label filtering."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        # Add tasks with different labels
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Work task", labels=["work"])
        task_manager.add_task("Personal task", labels=["personal"])

        # Test dry-run with label filtering
        from click.testing import CliRunner

        from fincli.cli import open_editor

        runner = CliRunner()
        result = runner.invoke(open_editor, ["--label", "work", "--dry-run"])

        assert result.exit_code == 0
        assert "📝 Found 1 tasks for editing:" in result.output
        assert "Work task" in result.output
        assert "Personal task" not in result.output
