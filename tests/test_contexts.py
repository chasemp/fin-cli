"""
Tests for the contexts module.
"""

import os
from unittest.mock import patch

import pytest

from fincli.contexts import ContextManager
from fincli.db import DatabaseManager
from fincli.tasks import TaskManager


class TestContextManager:
    """Test the ContextManager class."""

    def test_set_context(self):
        """Test setting a context."""
        # Clear any existing context
        if ContextManager.ENV_VAR in os.environ:
            del os.environ[ContextManager.ENV_VAR]

        ContextManager.set_context("work")
        assert os.environ[ContextManager.ENV_VAR] == "work"

    def test_get_current_context_default(self):
        """Test getting current context when none is set."""
        # Clear any existing context
        if ContextManager.ENV_VAR in os.environ:
            del os.environ[ContextManager.ENV_VAR]

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
                assert os.environ[ContextManager.ENV_VAR] == name
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

    def test_default_context_for_existing_tasks(self, temp_db_path):
        """Test that existing tasks get default context."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)

        # Create task without specifying context
        task_id = task_manager.add_task("Test task")

        # Retrieve task and verify it has default context
        task = task_manager.get_task(task_id)
        assert task["context"] == "default"
