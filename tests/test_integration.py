"""
Integration tests for FinCLI.

Tests the full integration between CLI commands and database operations.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from fincli.db import DatabaseManager
from fincli.tasks import TaskManager


class TestIntegration:
    """Test full CLI to database integration."""

    def test_full_cli_to_database_flow(self, temp_db_path, monkeypatch):
        """Test complete flow from CLI command to database storage."""
        # Set up environment
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Run CLI command
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "fincli.cli",
                "add-task",
                "Integration test task",
                "--label",
                "test",
                "--label",
                "integration",
            ],
            capture_output=True,
            text=True,
            env={"FIN_DB_PATH": temp_db_path, **os.environ},
        )

        assert result.returncode == 0
        assert (
            '✅ Task added: "Integration test task" [integration, test]'
            in result.stdout
        )

        # Verify in database
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        tasks = task_manager.list_tasks()

        assert len(tasks) == 1
        assert tasks[0]["content"] == "Integration test task"
        assert set(tasks[0]["labels"]) == {"test", "integration"}

    def test_multiple_cli_operations(self, temp_db_path, monkeypatch):
        """Test multiple CLI operations on the same database."""
        # Set up environment
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Add first task
        result1 = subprocess.run(
            [
                sys.executable,
                "-m",
                "fincli.cli",
                "add-task",
                "First task",
                "--label",
                "first",
            ],
            capture_output=True,
            text=True,
            env={"FIN_DB_PATH": temp_db_path, **os.environ},
        )

        assert result1.returncode == 0

        # Add second task
        result2 = subprocess.run(
            [
                sys.executable,
                "-m",
                "fincli.cli",
                "add-task",
                "Second task",
                "--label",
                "second",
            ],
            capture_output=True,
            text=True,
            env={"FIN_DB_PATH": temp_db_path, **os.environ},
        )

        assert result2.returncode == 0

        # Verify both tasks in database
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        tasks = task_manager.list_tasks()

        assert len(tasks) == 2
        task_contents = {task["content"] for task in tasks}
        assert "First task" in task_contents
        assert "Second task" in task_contents

    def test_cli_error_handling(self, temp_db_path, monkeypatch):
        """Test CLI error handling and validation."""
        # Set up environment
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Test with missing content
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "fincli.cli",
                "add-task",
            ],
            capture_output=True,
            text=True,
            env={"FIN_DB_PATH": temp_db_path, **os.environ},
        )

        assert result.returncode != 0
        assert "Missing argument" in result.stderr

        # Verify no tasks were added
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        tasks = task_manager.list_tasks()

        assert len(tasks) == 0

    def test_database_persistence_across_cli_calls(self, temp_db_path, monkeypatch):
        """Test that database persists data across multiple CLI calls."""
        # Set up environment
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Add task via CLI
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "fincli.cli",
                "add-task",
                "Persistent task",
                "--label",
                "persistent",
            ],
            capture_output=True,
            text=True,
            env={"FIN_DB_PATH": temp_db_path, **os.environ},
        )

        assert result.returncode == 0

        # Verify task exists
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        tasks = task_manager.list_tasks()

        assert len(tasks) == 1
        assert tasks[0]["content"] == "Persistent task"

    def test_special_characters_integration(self, temp_db_path, monkeypatch):
        """Test handling of special characters in integration."""
        # Set up environment
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        special_content = "Task with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "fincli.cli",
                "add-task",
                special_content,
                "--label",
                "special",
            ],
            capture_output=True,
            text=True,
            env={"FIN_DB_PATH": temp_db_path, **os.environ},
        )

        assert result.returncode == 0

        # Verify in database
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        tasks = task_manager.list_tasks()

        assert len(tasks) == 1
        assert tasks[0]["content"] == special_content

    def test_label_normalization_integration(self, temp_db_path, monkeypatch):
        """Test label normalization in integration."""
        # Set up environment
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "fincli.cli",
                "add-task",
                "Task with mixed case labels",
                "--label",
                "WORK",
                "--label",
                "Urgent",
                "--label",
                "  test  ",
            ],
            capture_output=True,
            text=True,
            env={"FIN_DB_PATH": temp_db_path, **os.environ},
        )

        assert result.returncode == 0
        assert (
            '✅ Task added: "Task with mixed case labels" [test, urgent, work]'
            in result.stdout
        )

        # Verify in database
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        tasks = task_manager.list_tasks()

        assert len(tasks) == 1
        assert set(tasks[0]["labels"]) == {"work", "urgent", "test"}


class TestRealDatabase:
    """Tests using the real database location."""

    def test_real_database_creation(self, monkeypatch, allow_real_database):
        """Test that real database is created in ~/.fin/."""
        # Use a temporary home directory
        with tempfile.TemporaryDirectory() as tmp_home:
            monkeypatch.setenv("HOME", tmp_home)

            # Create database manager (should create ~/.fin/tasks.db)
            db_manager = DatabaseManager()

            # Verify directory and file exist
            fin_dir = Path(tmp_home) / "fin"
            db_path = fin_dir / "tasks.db"

            assert fin_dir.exists()
            assert db_path.exists()

            # Add a task
            task_manager = TaskManager(db_manager)
            task_id = task_manager.add_task("Real database test")

            # Verify task was added
            task = task_manager.get_task(task_id)
            assert task is not None
            assert task["content"] == "Real database test"

    def test_real_database_persistence(self, monkeypatch, allow_real_database):
        """Test that real database persists data."""
        # Use a temporary home directory
        with tempfile.TemporaryDirectory() as tmp_home:
            monkeypatch.setenv("HOME", tmp_home)

            # Create first manager and add task
            manager1 = DatabaseManager()
            task_manager1 = TaskManager(manager1)
            task_id = task_manager1.add_task("Persistent real task")

            # Create second manager and verify task exists
            manager2 = DatabaseManager()
            task_manager2 = TaskManager(manager2)
            task = task_manager2.get_task(task_id)

            assert task is not None
            assert task["content"] == "Persistent real task"
