"""
Tests for the fine command functionality.

Tests the fine command which opens tasks in an external editor.
"""

from datetime import date
import os
import sys
from unittest.mock import patch

import pytest

from fincli.db import DatabaseManager
from fincli.editor import EditorManager
from fincli.tasks import TaskManager


class TestFineCommand:
    """Test the fine command functionality."""

    def test_get_editor_with_env(self, monkeypatch):
        """Test getting editor from environment variable."""
        monkeypatch.setenv("EDITOR", "vim")
        from fincli.utils import get_editor

        editor = get_editor()
        assert editor == "vim"

    def test_get_editor_fallback(self, monkeypatch):
        """Test getting editor fallback when EDITOR not set."""
        monkeypatch.delenv("EDITOR", raising=False)
        from fincli.utils import get_editor

        editor = get_editor()
        assert editor in ["nano", "vim", "code", "subl"]

    def test_parse_task_line_valid(self, temp_db_path, monkeypatch):
        """Test parsing a valid task line."""
        # Set environment variable to use temp database
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        from fincli.editor import EditorManager

        # Use the fixture-provided database manager
        db_manager = DatabaseManager(temp_db_path)
        line = "[ ] 2025-07-30 09:15  Write unit tests  #testing"
        editor_manager = EditorManager(db_manager)
        result = editor_manager.parse_task_line(line)

        assert result is not None
        assert result["status"] == "[ ]"
        assert result["timestamp"] == "2025-07-30 09:15"
        assert result["content"] == "Write unit tests"
        assert result["labels"] == ["testing"]
        assert result["is_completed"] is False

    def test_parse_task_line_completed(self, temp_db_path, monkeypatch):
        """Test parsing a completed task line."""
        # Set environment variable to use temp database
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        from fincli.editor import EditorManager

        # Use the fixture-provided database manager
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

        from fincli.editor import EditorManager

        # Use the fixture-provided database manager
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

        from fincli.editor import EditorManager

        # Use the fixture-provided database manager
        db_manager = DatabaseManager(temp_db_path)
        line = "Invalid task line format"
        editor_manager = EditorManager(db_manager)
        result = editor_manager.parse_task_line(line)

        assert result is None

    def test_find_matching_task(self, db_manager):
        """Test finding matching tasks."""
        task_manager = TaskManager(db_manager)
        task_id = task_manager.add_task("Test task", labels=["work"])
        _ = task_manager.get_task(task_id)

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

        from fincli.editor import EditorManager

        # Use the fixture-provided database manager
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add a test task
        task_id = task_manager.add_task("Test task for editing", labels=["work"])
        _ = task_manager.get_task(task_id)

        # Test finding the task - pass task_info with task_id
        task_info = {"task_id": task_id}
        found_id = editor_manager.find_matching_task(task_info)
        assert found_id == task_id

    def test_fine_command_safety_checks(self, db_manager):
        """Test fine command safety checks."""
        from fincli.editor import EditorManager

        editor_manager = EditorManager(db_manager)

        # Test that editor safety flag is initially False
        assert editor_manager._editor_opened is False

        # Test that we can check if editor was opened
        assert not editor_manager._editor_opened

    def test_editor_manager_safety_flag(self, db_manager):
        """Test editor manager safety flag functionality."""
        from fincli.editor import EditorManager

        editor_manager = EditorManager(db_manager)

        # Initially, no editor has been opened
        assert editor_manager._editor_opened is False

        # Simulate opening an editor (this would normally happen in real usage)
        # For testing, we just check the flag behavior
        assert not editor_manager._editor_opened


class TestFineStandaloneCommand:
    """Test the fine command as a standalone command."""

    def test_fine_command_help(self, cli_runner, db_manager):
        """Test fine command help output."""
        from fincli.cli import cli

        result = cli_runner.invoke(cli, ["open-editor", "--help"])
        assert result.exit_code == 0
        assert "open-editor" in result.output.lower()
        assert "edit" in result.output.lower()

    def test_fine_command_dry_run(self, cli_runner, db_manager):
        """Test fine command with dry run flag."""
        from fincli.cli import cli

        result = cli_runner.invoke(cli, ["open-editor", "--dry-run"])
        assert result.exit_code == 0
        # When there are no tasks, the command should indicate that
        assert "no tasks found" in result.output.lower()

    def test_fine_command_with_label_filter(self, cli_runner, db_manager):
        """Test fine command with label filter."""
        from fincli.cli import cli

        result = cli_runner.invoke(cli, ["open-editor", "-l", "work"])
        assert result.exit_code == 0
        # When there are no tasks, the command should indicate that
        assert "no tasks found" in result.output.lower()
