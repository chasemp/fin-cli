"""
Tests for main function label filtering and default filter behavior.

This module tests the main entry point function's handling of:
1. Default label filters (e.g., NOT backlog AND NOT dismissed)
2. Explicit label filtering via -l/--label flags
3. Interaction between explicit labels and default filters
"""

import os
import subprocess
import sys
import tempfile

import pytest

from fincli.config import Config
from fincli.db import DatabaseManager
from fincli.tasks import TaskManager


class TestMainFunctionFiltering:
    """Test main function filtering behavior."""

    def run_fin_command(self, args, db_path, config_dir=None):
        """Helper to run fin command with given arguments."""
        env = os.environ.copy()
        env["FIN_DB_PATH"] = db_path
        if config_dir:
            env["FIN_CONFIG_DIR"] = config_dir

        result = subprocess.run([sys.executable, "-m", "fincli.cli"] + args, capture_output=True, text=True, env=env)
        return result

    def test_label_flag_no_error(self, temp_db_path):
        """Test that -l flag doesn't produce 'No such option' error."""
        # Add a test task
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Work task", labels=["work"])

        result = self.run_fin_command(["-l", "work"], temp_db_path)

        assert result.returncode == 0
        assert "No such option: -l" not in result.stderr
        assert "Work task" in result.stdout

    def test_multiple_label_flags(self, temp_db_path):
        """Test multiple -l flags work correctly."""
        # Add test tasks
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Work task", labels=["work"])
        task_manager.add_task("Urgent task", labels=["urgent"])
        task_manager.add_task("Both task", labels=["work", "urgent"])

        result = self.run_fin_command(["-l", "work", "-l", "urgent"], temp_db_path)

        assert result.returncode == 0
        assert "Work task" in result.stdout
        assert "Urgent task" in result.stdout
        assert "Both task" in result.stdout

    def test_verbose_shows_explicit_label_info(self, temp_db_path):
        """Test that verbose mode shows explicit label information."""
        # Add a test task
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Work task", labels=["work"])

        result = self.run_fin_command(["-l", "work", "-v"], temp_db_path)

        assert result.returncode == 0
        assert "Labels: work" in result.stdout

    def test_long_label_flag_works(self, temp_db_path):
        """Test that --label flag works the same as -l."""
        # Add a test task
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Urgent task", labels=["urgent"])

        result = self.run_fin_command(["--label", "urgent"], temp_db_path)

        assert result.returncode == 0
        assert "Urgent task" in result.stdout

    def test_mixed_short_and_long_label_flags(self, temp_db_path):
        """Test mixing -l and --label flags."""
        # Add test tasks
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Work task", labels=["work"])
        task_manager.add_task("Urgent task", labels=["urgent"])

        result = self.run_fin_command(["-l", "work", "--label", "urgent"], temp_db_path)

        assert result.returncode == 0
        assert "Work task" in result.stdout
        assert "Urgent task" in result.stdout

    def test_no_tasks_found_with_label_filter(self, temp_db_path):
        """Test behavior when no tasks match label filter."""
        # Add a task that won't match
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Work task", labels=["work"])

        result = self.run_fin_command(["-l", "nonexistent"], temp_db_path)

        assert result.returncode == 0
        assert "No open tasks found" in result.stdout

    def test_label_filtering_case_insensitive(self, temp_db_path):
        """Test that label filtering is case insensitive."""
        # Add a test task
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Work task", labels=["work"])

        # Test uppercase label
        result = self.run_fin_command(["-l", "WORK"], temp_db_path)

        assert result.returncode == 0
        assert "Work task" in result.stdout

    def test_add_task_command_not_affected(self, temp_db_path):
        """Test that add-task command still works correctly with labels."""
        result = self.run_fin_command(["add-task", "New task", "--label", "test"], temp_db_path)

        assert result.returncode == 0
        assert "Task added" in result.stdout

    def test_list_command_not_affected(self, temp_db_path):
        """Test that explicit list command still works correctly."""
        # Add a test task
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Work task", labels=["work"])

        result = self.run_fin_command(["list", "--label", "work"], temp_db_path)

        assert result.returncode == 0
        assert "Work task" in result.stdout

    def test_default_filter_excludes_backlog_when_configured(self, temp_db_path):
        """Test that default filter excludes backlog when properly configured."""
        # Add test tasks
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Normal task", labels=["normal"])
        task_manager.add_task("Backlog task", labels=["backlog"])

        # Set up config with default filter
        with tempfile.TemporaryDirectory() as config_dir:
            # Set config environment
            old_config_dir = os.environ.get("FIN_CONFIG_DIR")
            os.environ["FIN_CONFIG_DIR"] = config_dir

            try:
                # Create config and set filter
                config = Config()
                config.set_context_default_label_filter("default", "NOT backlog")

                # Run command
                result = self.run_fin_command([], temp_db_path, config_dir)

                assert result.returncode == 0
                assert "Normal task" in result.stdout
                assert "Backlog task" not in result.stdout

            finally:
                # Restore original config dir
                if old_config_dir:
                    os.environ["FIN_CONFIG_DIR"] = old_config_dir
                elif "FIN_CONFIG_DIR" in os.environ:
                    del os.environ["FIN_CONFIG_DIR"]

    def test_explicit_label_overrides_default_filter(self, temp_db_path):
        """Test that explicit -l flag overrides default filter."""
        # Add test tasks
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Normal task", labels=["normal"])
        task_manager.add_task("Backlog task", labels=["backlog"])

        # Set up config with default filter
        with tempfile.TemporaryDirectory() as config_dir:
            # Set config environment
            old_config_dir = os.environ.get("FIN_CONFIG_DIR")
            os.environ["FIN_CONFIG_DIR"] = config_dir

            try:
                # Create config and set filter
                config = Config()
                config.set_context_default_label_filter("default", "NOT backlog")

                # Run command with explicit backlog filter (should override default)
                result = self.run_fin_command(["-l", "backlog"], temp_db_path, config_dir)

                assert result.returncode == 0
                assert "Backlog task" in result.stdout
                assert "Normal task" not in result.stdout

            finally:
                # Restore original config dir
                if old_config_dir:
                    os.environ["FIN_CONFIG_DIR"] = old_config_dir
                elif "FIN_CONFIG_DIR" in os.environ:
                    del os.environ["FIN_CONFIG_DIR"]
