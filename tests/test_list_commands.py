"""Tests for the list and list-tasks commands to ensure consistency and proper default behavior."""

from datetime import datetime, timedelta
import sqlite3

from click.testing import CliRunner
import pytest

from fincli.cli import cli
from fincli.db import DatabaseManager
from fincli.tasks import TaskManager


@pytest.fixture
def cli_runner():
    """Provide a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database path."""
    return str(tmp_path / "test_tasks.db")


@pytest.fixture
def populated_db(temp_db_path):
    """Provide a database with sample tasks from different dates."""
    db_manager = DatabaseManager(temp_db_path)
    task_manager = TaskManager(db_manager)

    # Add tasks from different dates
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    three_days_ago = today - timedelta(days=3)

    # Today's tasks
    task_manager.add_task("Today's task 1", labels=["work"])
    task_manager.add_task("Today's task 2", labels=["personal"])

    # Yesterday's tasks
    yesterday_task_id = task_manager.add_task("Yesterday's task", labels=["urgent"])

    # Three days ago task (completed)
    old_task_id = task_manager.add_task("Old completed task", labels=["done"])

    # Mark some as completed with specific dates
    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET completed_at = ? WHERE id = ?",
            (yesterday.strftime("%Y-%m-%d 12:00:00"), yesterday_task_id),
        )
        cursor.execute(
            "UPDATE tasks SET completed_at = ? WHERE id = ?",
            (three_days_ago.strftime("%Y-%m-%d 12:00:00"), old_task_id),
        )
        conn.commit()

    return temp_db_path


class TestListCommandsConsistency:
    """Test that list and list-tasks commands behave identically."""

    def test_list_and_list_tasks_identical_help(self, cli_runner):
        """Test that both commands have identical help text."""
        list_help = cli_runner.invoke(cli, ["list", "--help"])
        list_tasks_help = cli_runner.invoke(cli, ["list-tasks", "--help"])

        assert list_help.exit_code == 0
        assert list_tasks_help.exit_code == 0

        # Extract just the options section (skip command name and description)
        list_options = list_help.output.split("Options:")[1]
        list_tasks_options = list_tasks_help.output.split("Options:")[1]

        assert list_options == list_tasks_options

    def test_list_and_list_tasks_identical_output(self, cli_runner, populated_db):
        """Test that both commands produce identical output."""
        list_result = cli_runner.invoke(cli, ["list"], env={"FIN_DB_PATH": populated_db})
        list_tasks_result = cli_runner.invoke(cli, ["list-tasks"], env={"FIN_DB_PATH": populated_db})

        assert list_result.exit_code == 0
        assert list_tasks_result.exit_code == 0
        assert list_result.output == list_tasks_result.output

    def test_list_and_list_tasks_identical_with_days(self, cli_runner, populated_db):
        """Test that both commands produce identical output with --days parameter."""
        list_result = cli_runner.invoke(cli, ["list", "--days", "1"], env={"FIN_DB_PATH": populated_db})
        list_tasks_result = cli_runner.invoke(cli, ["list-tasks", "--days", "1"], env={"FIN_DB_PATH": populated_db})

        assert list_result.exit_code == 0
        assert list_tasks_result.exit_code == 0
        assert list_result.output == list_tasks_result.output

    def test_list_and_list_tasks_identical_with_status(self, cli_runner, populated_db):
        """Test that both commands produce identical output with --status parameter."""
        list_result = cli_runner.invoke(cli, ["list", "--status", "all"], env={"FIN_DB_PATH": populated_db})
        list_tasks_result = cli_runner.invoke(cli, ["list-tasks", "--status", "all"], env={"FIN_DB_PATH": populated_db})

        assert list_result.exit_code == 0
        assert list_tasks_result.exit_code == 0
        assert list_result.output == list_tasks_result.output


class TestListCommandsDefaultBehavior:
    """Test the default behavior of list commands (2 days for open tasks)."""

    def test_default_shows_only_open_tasks_from_recent_days(self, cli_runner, populated_db):
        """Test that default behavior shows only open tasks from today and yesterday."""
        result = cli_runner.invoke(cli, ["list"], env={"FIN_DB_PATH": populated_db})

        assert result.exit_code == 0

        # Should show today's open tasks
        assert "Today's task 1" in result.output
        assert "Today's task 2" in result.output

        # Should NOT show completed tasks
        assert "Yesterday's task" not in result.output  # This was completed
        assert "Old completed task" not in result.output  # This was completed and old

        # Should NOT show tasks from 3+ days ago
        assert "Old completed task" not in result.output

    def test_default_with_status_all_shows_all_tasks(self, cli_runner, populated_db):
        """Test that --status all shows all tasks within the default 2-day limit."""
        result = cli_runner.invoke(cli, ["list", "--status", "all"], env={"FIN_DB_PATH": populated_db})

        assert result.exit_code == 0

        # Should show all tasks within 2 days (today and yesterday)
        assert "Today's task 1" in result.output
        assert "Today's task 2" in result.output
        assert "Yesterday's task" in result.output

        # Should NOT show tasks from 3+ days ago (even with --status all)
        # because the default 2-day limit applies before status filtering
        assert "Old completed task" not in result.output

    def test_days_parameter_overrides_default(self, cli_runner, populated_db):
        """Test that --days parameter overrides the default 2-day behavior."""
        result = cli_runner.invoke(cli, ["list", "--days", "1"], env={"FIN_DB_PATH": populated_db})

        assert result.exit_code == 0

        # Should show only today's tasks
        assert "Today's task 1" in result.output
        assert "Today's task 2" in result.output

        # Should NOT show yesterday's tasks
        assert "Yesterday's task" not in result.output

    def test_today_flag_overrides_default(self, cli_runner, populated_db):
        """Test that --today flag overrides the default behavior."""
        result = cli_runner.invoke(cli, ["list", "--today"], env={"FIN_DB_PATH": populated_db})

        assert result.exit_code == 0

        # Should show only today's tasks
        assert "Today's task 1" in result.output
        assert "Today's task 2" in result.output

        # Should NOT show yesterday's tasks
        assert "Yesterday's task" not in result.output

    def test_days_parameter_overrides_default_completely(self, cli_runner, populated_db):
        """Test that --days parameter completely overrides the default 2-day behavior."""
        result = cli_runner.invoke(cli, ["list", "--days", "5", "--status", "all"], env={"FIN_DB_PATH": populated_db})

        assert result.exit_code == 0

        # Should show all tasks within 5 days, including the old completed task
        assert "Today's task 1" in result.output
        assert "Today's task 2" in result.output
        assert "Yesterday's task" in result.output
        assert "Old completed task" in result.output  # Now within 5-day range


class TestListCommandsValidation:
    """Test validation logic in list commands."""

    def test_today_and_days_conflict_detected(self, cli_runner, populated_db):
        """Test that using both --today and --days together is rejected."""
        result = cli_runner.invoke(cli, ["list", "--today", "--days", "3"], env={"FIN_DB_PATH": populated_db})

        assert result.exit_code == 0  # Click doesn't exit with error for validation failures
        assert "❌ Error: Cannot use both --today and --days together" in result.output
        assert "--today overrides --days, so they are mutually exclusive" in result.output

    def test_today_and_days_conflict_detected_list_tasks(self, cli_runner, populated_db):
        """Test that list-tasks also detects the conflict."""
        result = cli_runner.invoke(cli, ["list-tasks", "--today", "--days", "3"], env={"FIN_DB_PATH": populated_db})

        assert result.exit_code == 0
        assert "❌ Error: Cannot use both --today and --days together" in result.output

    def test_today_without_days_allowed(self, cli_runner, populated_db):
        """Test that --today without --days is allowed."""
        result = cli_runner.invoke(cli, ["list", "--today"], env={"FIN_DB_PATH": populated_db})

        assert result.exit_code == 0
        assert "❌ Error" not in result.output

    def test_days_without_today_allowed(self, cli_runner, populated_db):
        """Test that --days without --today is allowed."""
        result = cli_runner.invoke(cli, ["list", "--days", "5"], env={"FIN_DB_PATH": populated_db})

        assert result.exit_code == 0
        assert "❌ Error" not in result.output


class TestListCommandsParameterTypes:
    """Test that parameters are properly typed and handled."""

    def test_days_parameter_accepts_integer(self, cli_runner, populated_db):
        """Test that --days accepts integer values."""
        result = cli_runner.invoke(cli, ["list", "--days", "7"], env={"FIN_DB_PATH": populated_db})

        assert result.exit_code == 0
        assert "❌ Error" not in result.output

    def test_days_parameter_rejects_non_integer(self, cli_runner, populated_db):
        """Test that --days rejects non-integer values."""
        result = cli_runner.invoke(cli, ["list", "--days", "abc"], env={"FIN_DB_PATH": populated_db})

        # Click should handle this validation
        assert result.exit_code != 0 or "Invalid value" in result.output

    def test_status_parameter_accepts_valid_values(self, cli_runner, populated_db):
        """Test that --status accepts valid status values."""
        valid_statuses = ["open", "o", "completed", "done", "d", "all", "a"]

        for status in valid_statuses:
            result = cli_runner.invoke(cli, ["list", "--status", status], env={"FIN_DB_PATH": populated_db})
            assert result.exit_code == 0, f"Status '{status}' should be valid"

    def test_status_parameter_rejects_invalid_values(self, cli_runner, populated_db):
        """Test that --status rejects invalid status values."""
        result = cli_runner.invoke(cli, ["list", "--status", "invalid"], env={"FIN_DB_PATH": populated_db})

        # Click should handle this validation
        assert result.exit_code != 0 or "Invalid value" in result.output


class TestListCommandsIntegration:
    """Test integration aspects of list commands."""

    def test_verbose_flag_works_both_commands(self, cli_runner, populated_db):
        """Test that --verbose works with both commands."""
        list_result = cli_runner.invoke(cli, ["list", "--verbose"], env={"FIN_DB_PATH": populated_db})
        list_tasks_result = cli_runner.invoke(cli, ["list-tasks", "--verbose"], env={"FIN_DB_PATH": populated_db})

        assert list_result.exit_code == 0
        assert list_tasks_result.exit_code == 0

        # Both should show verbose output
        assert "DatabaseManager using path:" in list_result.output
        assert "DatabaseManager using path:" in list_tasks_result.output

    def test_label_filtering_works_both_commands(self, cli_runner, populated_db):
        """Test that label filtering works with both commands."""
        list_result = cli_runner.invoke(cli, ["list", "--label", "work"], env={"FIN_DB_PATH": populated_db})
        list_tasks_result = cli_runner.invoke(cli, ["list-tasks", "--label", "work"], env={"FIN_DB_PATH": populated_db})

        assert list_result.exit_code == 0
        assert list_tasks_result.exit_code == 0

        # Both should show only work tasks
        assert "Today's task 1" in list_result.output  # Has work label
        assert "Today's task 2" not in list_result.output  # Has personal label
        assert "Today's task 1" in list_tasks_result.output
        assert "Today's task 2" not in list_tasks_result.output
