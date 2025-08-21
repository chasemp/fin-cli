"""
Tests for the contexts module.
"""

from unittest.mock import patch

import pytest

from fincli.cli import cli
from fincli.config import Config
from fincli.contexts import ContextManager
from fincli.db import DatabaseManager
from fincli.tasks import TaskManager


class TestContextManager:
    """Test the ContextManager class."""

    def test_set_context(self):
        """Test setting a context."""
        # Clear any existing context
        ContextManager.clear_context()

        ContextManager.set_context("work")
        assert ContextManager.get_current_context() == "work"

    def test_get_current_context_default(self):
        """Test getting current context when none is set."""
        # Clear any existing context
        ContextManager.clear_context()

        assert ContextManager.get_current_context() == "default"

    def test_get_current_context_set(self):
        """Test getting current context when one is set."""
        ContextManager.set_context("personal")
        assert ContextManager.get_current_context() == "personal"

    def test_clear_context(self):
        """Test clearing context."""
        ContextManager.set_context("work")
        ContextManager.clear_context()
        assert ContextManager.get_current_context() == "default"

    def test_invalid_context_name(self):
        """Test that invalid context names are rejected."""
        with pytest.raises(ValueError):
            ContextManager.set_context("")

        with pytest.raises(ValueError):
            ContextManager.set_context("and")  # Reserved word

        with pytest.raises(ValueError):
            ContextManager.set_context("context")  # Reserved word

    def test_valid_context_names(self):
        """Test that valid context names are accepted."""
        valid_names = ["work", "personal", "project_a", "urgent-tasks", "home_office"]

        for name in valid_names:
            try:
                ContextManager.set_context(name)
                assert ContextManager.get_current_context() == name
            except ValueError:
                pytest.fail(f"Valid context name '{name}' was rejected")

    def test_list_contexts(self, temp_db_path):
        """Test listing contexts from database."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Add tasks with different contexts
        task_manager.add_task("Work task", context="work")
        task_manager.add_task("Personal task", context="personal")
        task_manager.add_task("Default task", context="default")

        contexts = ContextManager.list_contexts(db_manager)

        # Should include all contexts, with default first
        assert "default" in contexts
        assert "work" in contexts
        assert "personal" in contexts
        assert contexts[0] == "default"  # Default should be first


class TestContextIntegration:
    """Test context integration with other components."""

    def test_task_creation_with_context(self, temp_db_path):
        """Test that tasks are created with the current context."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Set context and create task
        ContextManager.set_context("work")
        task_id = task_manager.add_task("Test task", context="work")

        # Retrieve task and verify context
        task = task_manager.get_task(task_id)
        assert task["context"] == "work"

    def test_task_filtering_by_context(self, temp_db_path):
        """Test that tasks are filtered by context."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Create tasks in different contexts
        task_manager.add_task("Work task 1", context="work")
        task_manager.add_task("Work task 2", context="work")
        task_manager.add_task("Personal task", context="personal")

        # List tasks in work context
        work_tasks = task_manager.list_tasks(context="work")
        assert len(work_tasks) == 2
        assert all(task["context"] == "work" for task in work_tasks)

        # List tasks in personal context
        personal_tasks = task_manager.list_tasks(context="personal")
        assert len(personal_tasks) == 1
        assert all(task["context"] == "personal" for task in personal_tasks)

    def test_default_context_for_existing_tasks(self, isolated_cli_runner):
        """Test that existing tasks without context get default context."""
        # Add a task without specifying context
        result = isolated_cli_runner.invoke(cli, ["add", "Test task without context"])
        assert result.exit_code == 0

        # List tasks and verify it appears in default context
        result = isolated_cli_runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "Test task without context" in result.output


class TestContextDefaultLabelFilters:
    """Test context default label filter functionality."""

    def test_set_context_default_label_filter(self, isolated_cli_runner):
        """Test setting a default label filter for a context."""
        config = Config()

        # Set default label filter for default context
        config.set_context_default_label_filter("default", "NOT backlog")

        # Verify it was set
        assert config.get_context_default_label_filter("default") == "NOT backlog"

    def test_remove_context_default_label_filter(self, isolated_cli_runner):
        """Test removing a default label filter for a context."""
        config = Config()

        # Set and then remove a filter
        config.set_context_default_label_filter("work", "NOT personal")
        assert config.get_context_default_label_filter("work") == "NOT personal"

        config.remove_context_default_label_filter("work")
        assert config.get_context_default_label_filter("work") is None

    def test_get_all_context_default_label_filters(self, isolated_cli_runner):
        """Test getting all context default label filters."""
        config = Config()

        # Set filters for multiple contexts
        config.set_context_default_label_filter("default", "NOT backlog")
        config.set_context_default_label_filter("work", "NOT personal")

        all_filters = config.get_all_context_default_label_filters()
        assert all_filters["default"] == "NOT backlog"
        assert all_filters["work"] == "NOT personal"

    def test_default_label_filter_applied_when_no_explicit_labels(self, isolated_cli_runner, isolated_config):
        """Test that default label filter is applied when no explicit labels provided."""
        # Add tasks with different labels using explicit label options
        result = isolated_cli_runner.invoke(cli, ["add", "Task 1", "--label", "backlog"])
        assert result.exit_code == 0

        result = isolated_cli_runner.invoke(cli, ["add", "Task 2", "--label", "work"])
        assert result.exit_code == 0

        result = isolated_cli_runner.invoke(cli, ["add", "Task 3", "--label", "urgent"])
        assert result.exit_code == 0

        # Set default label filter to exclude backlog
        config = Config()
        config.set_context_default_label_filter("default", "NOT backlog")

        # List tasks without explicit labels - should exclude backlog tasks
        result = isolated_cli_runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "Task 1" not in result.output  # Should be filtered out
        assert "Task 2" in result.output  # Should be included
        assert "Task 3" in result.output  # Should be included

    def test_explicit_labels_override_default_filter(self, isolated_cli_runner, isolated_config):
        """Test that explicit labels override the default label filter."""
        # Add tasks with different labels using explicit label options
        result = isolated_cli_runner.invoke(cli, ["add", "Task 1", "--label", "backlog"])
        assert result.exit_code == 0

        result = isolated_cli_runner.invoke(cli, ["add", "Task 2", "--label", "work"])
        assert result.exit_code == 0

        # Set default label filter to exclude backlog
        config = Config()
        config.set_context_default_label_filter("default", "NOT backlog")

        # List tasks with explicit label filter - should override default
        result = isolated_cli_runner.invoke(cli, ["list", "-l", "backlog"])
        assert result.exit_code == 0
        assert "Task 1" in result.output  # Should be included due to explicit filter
        assert "Task 2" not in result.output  # Should be excluded due to explicit filter

    def test_default_label_filter_in_verbose_output(self, isolated_cli_runner, isolated_config):
        """Test that default label filter is shown in verbose output."""
        # Set default label filter
        config = Config()
        config.set_context_default_label_filter("default", "NOT backlog")

        # List tasks with verbose flag
        result = isolated_cli_runner.invoke(cli, ["list", "-v"])
        assert result.exit_code == 0
        assert "Default label filter: NOT backlog" in result.output

    def test_no_default_label_filter_when_explicit_labels(self, isolated_cli_runner, isolated_config):
        """Test that default label filter is not shown when explicit labels are used."""
        # Set default label filter
        config = Config()
        config.set_context_default_label_filter("default", "NOT backlog")

        # List tasks with explicit label filter and verbose flag
        result = isolated_cli_runner.invoke(cli, ["list", "-l", "work", "-v"])
        assert result.exit_code == 0
        assert "Default label filter: NOT backlog" not in result.output
        assert "Labels: work" in result.output


class TestContextLabelFilterCLI:
    """Test CLI commands for managing context default label filters."""

    def test_context_label_filter_set(self, isolated_cli_runner):
        """Test setting a context default label filter via CLI."""
        result = isolated_cli_runner.invoke(cli, ["context-label-filter", "set", "default", "--filter", "NOT backlog"])
        assert result.exit_code == 0
        assert "Set default label filter for context 'default': NOT backlog" in result.output

        # Verify it was actually set
        config = Config()
        assert config.get_context_default_label_filter("default") == "NOT backlog"

    def test_context_label_filter_get(self, isolated_cli_runner):
        """Test getting a context default label filter via CLI."""
        # Set a filter first
        config = Config()
        config.set_context_default_label_filter("work", "NOT personal")

        result = isolated_cli_runner.invoke(cli, ["context-label-filter", "get", "work"])
        assert result.exit_code == 0
        assert "Context 'work' default label filter: NOT personal" in result.output

    def test_context_label_filter_get_nonexistent(self, isolated_cli_runner):
        """Test getting a context default label filter that doesn't exist."""
        result = isolated_cli_runner.invoke(cli, ["context-label-filter", "get", "nonexistent"])
        assert result.exit_code == 0
        assert "has no default label filter" in result.output

    def test_context_label_filter_remove(self, isolated_cli_runner):
        """Test removing a context default label filter via CLI."""
        # Set a filter first
        config = Config()
        config.set_context_default_label_filter("work", "NOT personal")
        assert config.get_context_default_label_filter("work") == "NOT personal"

        result = isolated_cli_runner.invoke(cli, ["context-label-filter", "remove", "work"])
        assert result.exit_code == 0
        assert "Removed default label filter for context 'work'" in result.output

        # Verify it was actually removed
        assert config.get_context_default_label_filter("work") is None

    def test_context_label_filter_list(self, isolated_cli_runner):
        """Test listing all context default label filters via CLI."""
        # Set some filters first
        config = Config()
        config.set_context_default_label_filter("default", "NOT backlog")
        config.set_context_default_label_filter("work", "NOT personal")

        result = isolated_cli_runner.invoke(cli, ["context-label-filter", "list"])
        assert result.exit_code == 0
        assert "default: NOT backlog" in result.output
        assert "work: NOT personal" in result.output

    def test_context_label_filter_list_empty(self, isolated_cli_runner):
        """Test listing context default label filters when none exist."""
        result = isolated_cli_runner.invoke(cli, ["context-label-filter", "list"])
        assert result.exit_code == 0
        assert "No context default label filters configured" in result.output

    def test_context_label_filter_set_missing_arguments(self, isolated_cli_runner):
        """Test setting a context default label filter with missing arguments."""
        result = isolated_cli_runner.invoke(cli, ["context-label-filter", "set", "default"])
        assert result.exit_code == 1
        assert "Both context and filter are required for setting" in result.output

    def test_context_label_filter_get_missing_context(self, isolated_cli_runner):
        """Test getting a context default label filter with missing context."""
        result = isolated_cli_runner.invoke(cli, ["context-label-filter", "get"])
        assert result.exit_code == 1
        assert "Context name is required for getting filter" in result.output

    def test_context_label_filter_remove_missing_context(self, isolated_cli_runner):
        """Test removing a context default label filter with missing context."""
        result = isolated_cli_runner.invoke(cli, ["context-label-filter", "remove"])
        assert result.exit_code == 1
        assert "Context name is required for removing filter" in result.output
