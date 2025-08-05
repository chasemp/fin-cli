"""
Tests for the fins command functionality
"""

import subprocess
import sys
from datetime import date, timedelta

from fincli.cli import list_tasks
from fincli.db import DatabaseManager
from fincli.utils import format_task_for_display, get_date_range


class TestFinsCommand:
    """Test fins command functionality."""

    def test_format_task_for_display_open(self, db_manager):
        """Test formatting open tasks for display."""
        # Add a task
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)

        task_id = task_manager.add_task("Test open task", labels=["work", "urgent"])
        task = task_manager.get_task(task_id)

        formatted = format_task_for_display(task)

        assert formatted.startswith("[ ]")
        assert "Test open task" in formatted
        assert "#urgent,#work" in formatted

    def test_format_task_for_display_completed(self, db_manager):
        """Test formatting completed tasks for display."""
        # Add a task
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)

        task_id = task_manager.add_task("Test completed task", labels=["work"])
        task = task_manager.get_task(task_id)

        # Mark as completed
        import sqlite3

        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (task_id,),
            )
            conn.commit()

        # Get updated task
        task = task_manager.get_task(task_id)
        formatted = format_task_for_display(task)

        assert formatted.startswith("[x]")
        assert "Test completed task" in formatted
        assert "#work" in formatted

    def test_get_date_range(self):
        """Test date range calculation."""
        today, yesterday, week_ago = get_date_range(include_week=False)

        assert today == date.today()
        assert yesterday == today - timedelta(days=1)
        assert week_ago == today - timedelta(days=7)

    def test_query_tasks_empty(self, db_manager):
        """Test querying tasks when database is empty."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        tasks = task_manager.list_tasks(include_completed=True)
        formatted_tasks = [format_task_for_display(task) for task in tasks]
        assert formatted_tasks == []

    def test_query_tasks_today_open(self, db_manager):
        """Test querying today's open tasks."""
        # Add a task today
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)

        task_manager.add_task("Today's task")

        tasks = task_manager.list_tasks(include_completed=True)
        formatted_tasks = [format_task_for_display(task) for task in tasks]

        assert len(formatted_tasks) == 1
        assert "Today's task" in formatted_tasks[0]
        assert formatted_tasks[0].startswith("[ ]")

    def test_query_tasks_yesterday_completed(self, db_manager):
        """Test querying yesterday's completed tasks."""
        # Add a task
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)

        task_manager.add_task("Yesterday's task")

        # Mark as completed yesterday
        import sqlite3

        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            yesterday = date.today() - timedelta(days=1)
            # Get the task ID from the database
            cursor.execute(
                "SELECT id FROM tasks WHERE content = ?", ("Yesterday's task",)
            )
            task_id = cursor.fetchone()[0]
            cursor.execute(
                "UPDATE tasks SET completed_at = ? WHERE id = ?",
                (yesterday.strftime("%Y-%m-%d 12:00:00"), task_id),
            )
            conn.commit()

        tasks = task_manager.list_tasks(include_completed=True)
        formatted_tasks = [format_task_for_display(task) for task in tasks]

        assert len(formatted_tasks) == 1
        assert "Yesterday's task" in formatted_tasks[0]
        assert formatted_tasks[0].startswith("[x]")

    def test_query_tasks_week_flag(self, db_manager):
        """Test querying with --week flag."""
        # Add tasks for different days
        task_ids = []
        for i in range(5):
            from fincli.tasks import TaskManager

            task_manager = TaskManager(db_manager)

            task_id = task_manager.add_task(f"Task {i} days ago")
            task_ids.append(task_id)

        # Mark tasks as completed on different days
        import sqlite3

        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            for i, task_id in enumerate(task_ids):
                days_ago = date.today() - timedelta(days=i)
                cursor.execute(
                    "UPDATE tasks SET completed_at = ? WHERE id = ?",
                    (days_ago.strftime("%Y-%m-%d 12:00:00"), task_id),
                )
            conn.commit()

        # Query with week flag
        tasks = task_manager.list_tasks(include_completed=True)
        formatted_tasks = [format_task_for_display(task) for task in tasks]

        # Should include tasks from the past 7 days (including today)
        # We created 5 tasks, so we should have 5 completed tasks
        assert len(formatted_tasks) == 5

    def test_fins_command_help(self, cli_runner):
        """Test fins command help."""
        result = cli_runner.invoke(list_tasks, ["--help"])

        assert result.exit_code == 0
        assert "Query and display tasks" in result.output
        assert "--week" in result.output

    def test_fins_command_no_tasks(self, cli_runner, temp_db_path, monkeypatch):
        """Test fins command with no tasks."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        result = cli_runner.invoke(list_tasks, [])

        assert result.exit_code == 0
        assert "📝 No tasks found matching your criteria." in result.output

    def test_fins_command_with_tasks(self, cli_runner, temp_db_path, monkeypatch):
        """Test fins command with tasks."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        # Add a task
        db_manager = DatabaseManager(temp_db_path)
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)

        task_manager.add_task("Test task", labels=["work"])

        result = cli_runner.invoke(list_tasks, [])

        assert result.exit_code == 0
        assert "Test task" in result.output
        assert "#work" in result.output
        assert "[ ]" in result.output


class TestFinsIntegration:
    """Integration tests for fins command."""

    def test_fins_cli_execution(self, temp_db_path, monkeypatch):
        """Test fins command execution via subprocess."""
        # Set up environment
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Add a task
        subprocess.run(
            [
                sys.executable,
                "-m",
                "fincli.cli",
                "add-task",
                "Integration test task",
            ],
            capture_output=True,
            text=True,
        )

        # Run fins command
        result = subprocess.run(
            [sys.executable, "-m", "fincli.cli", "list-tasks"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Integration test task" in result.stdout

    def test_fins_week_flag(self, temp_db_path, monkeypatch):
        """Test fins command with --week flag."""
        # Set up environment
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Add a task
        subprocess.run(
            [sys.executable, "-m", "fincli.cli", "add-task", "Week test task"],
            capture_output=True,
            text=True,
        )

        # Run fins command with --week flag
        result = subprocess.run(
            [sys.executable, "-m", "fincli.cli", "list-tasks", "--week"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Week test task" in result.stdout

    def test_fins_output_format(self, temp_db_path, monkeypatch):
        """Test fins output format."""
        # Set up environment
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Add a task with labels
        subprocess.run(
            [
                sys.executable,
                "-m",
                "fincli.cli",
                "add-task",
                "Format test task",
                "--label",
                "work",
                "--label",
                "urgent",
            ],
            capture_output=True,
            text=True,
        )

        # Run fins command
        result = subprocess.run(
            [sys.executable, "-m", "fincli.cli", "list-tasks"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "[ ]" in result.stdout  # Open task indicator
        assert "Format test task" in result.stdout
        assert "#urgent,#work" in result.stdout  # Labels as hashtags
