"""
Tests for the hidden-labels CLI command.

Tests the new CLI command that shows information about hidden labels.
"""

import os
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestHiddenLabelsCLI:
    """Test the hidden-labels CLI command."""

    def test_hidden_labels_command_output(self, capsys):
        """Test that the hidden-labels command produces expected output."""
        # Mock the get_hidden_labels_info function
        with patch("fincli.utils.get_hidden_labels_info") as mock_get_info:
            mock_get_info.return_value = {
                "authority:full": "Task authority level (full = fin-cli controls both definition and status)",
                "source:slack": "Source system identifier",
                "mod:*": "Task modification timestamp (when task was last modified)",
            }

            # Call the command function directly (bypassing Click argument parsing)
            import io
            import sys

            from fincli.cli import hidden_labels_command

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            try:
                # Call the function directly without Click argument parsing
                hidden_labels_command.callback()
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout

            # Verify the output contains expected elements
            assert "🏷️  Hidden Labels (shown with -v/--verbose):" in output
            assert "authority:full: Task authority level" in output
            assert "source:slack: Source system identifier" in output
            assert "mod:*: Task modification timestamp" in output
            assert "💡 Use -v or --verbose with any command to see these labels" in output

    def test_hidden_labels_command_no_labels(self, capsys):
        """Test the hidden-labels command when no labels are configured."""
        # Mock the get_hidden_labels_info function to return empty dict
        with patch("fincli.utils.get_hidden_labels_info") as mock_get_info:
            mock_get_info.return_value = {}

            # Call the command function directly (bypassing Click argument parsing)
            import io
            import sys

            from fincli.cli import hidden_labels_command

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            try:
                # Call the function directly without Click argument parsing
                hidden_labels_command.callback()
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout

            # Verify the output for no labels
            assert "✨ No hidden labels configured" in output

    def test_hidden_labels_command_integration(self, capsys):
        """Test the hidden-labels command with real hidden labels data."""
        # Import the real function
        import io
        import sys

        # Call the command function directly (bypassing Click argument parsing)
        from fincli.cli import hidden_labels_command
        from fincli.utils import get_hidden_labels_info

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # Call the function directly without Click argument parsing
            hidden_labels_command.callback()
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        # Verify the output contains the expected structure
        assert "🏷️  Hidden Labels (shown with -v/--verbose):" in output
        assert "💡 Use -v or --verbose with any command to see these labels" in output

        # Should contain at least some of the expected labels
        expected_labels = ["authority:full", "source:slack", "mod:*"]
        found_labels = 0
        for label in expected_labels:
            if label in output:
                found_labels += 1

        # Should find at least some labels
        assert found_labels > 0

    def test_hidden_labels_command_formatting(self, capsys):
        """Test that the hidden-labels command formats output correctly."""
        # Mock the get_hidden_labels_info function
        with patch("fincli.utils.get_hidden_labels_info") as mock_get_info:
            mock_get_info.return_value = {
                "test:label": "Test description",
            }

            # Call the command function directly (bypassing Click argument parsing)
            import io
            import sys

            from fincli.cli import hidden_labels_command

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            try:
                # Call the function directly without Click argument parsing
                hidden_labels_command.callback()
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout

            # Verify the formatting
            lines = output.strip().split("\n")

            # Should have the header
            assert "🏷️  Hidden Labels (shown with -v/--verbose):" in lines

            # Should have the label with bullet point
            assert "   • test:label: Test description" in lines

            # Should have the tip
            assert "💡 Use -v or --verbose with any command to see these labels" in lines

    def test_hidden_labels_command_import_error_handling(self, capsys):
        """Test that the hidden-labels command handles import errors gracefully."""
        # Mock the import to fail
        with patch("fincli.utils.get_hidden_labels_info", side_effect=ImportError("Test import error")):
            # Call the command function directly (bypassing Click argument parsing)
            import io
            import sys

            from fincli.cli import hidden_labels_command

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            try:
                # Call the function directly without Click argument parsing
                hidden_labels_command.callback()
                output = sys.stdout.getvalue()

                # If we get here, the function didn't raise an exception
                # This means it handled the error gracefully
                assert "Error" in output or "error" in output
            except ImportError:
                # The function raised the ImportError as expected
                # This is also acceptable behavior
                pass
            finally:
                sys.stdout = old_stdout


class TestHiddenLabelsCLIExecution:
    """Test the hidden-labels command execution through subprocess."""

    def test_hidden_labels_command_execution(self):
        """Test that the hidden-labels command can be executed through the CLI."""
        # Create a temporary database path for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            tmp_db_path = tmp_db.name

        try:
            # Set environment variable for test database
            env = {"FIN_DB_PATH": tmp_db_path}

            # Run the command
            result = subprocess.run([sys.executable, "-m", "fincli.cli", "hidden-labels"], capture_output=True, text=True, env=env, cwd=os.getcwd())

            # Should execute successfully
            assert result.returncode == 0

            # Should produce output
            assert result.stdout
            assert "🏷️  Hidden Labels" in result.stdout

        finally:
            # Clean up
            if os.path.exists(tmp_db_path):
                os.unlink(tmp_db_path)

    def test_hidden_labels_command_help(self):
        """Test that the hidden-labels command shows help information."""
        # Create a temporary database path for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            tmp_db_path = tmp_db.name

        try:
            # Set environment variable for test database
            env = {"FIN_DB_PATH": tmp_db_path}

            # Run the command with help flag
            result = subprocess.run([sys.executable, "-m", "fincli.cli", "hidden-labels", "--help"], capture_output=True, text=True, env=env, cwd=os.getcwd())

            # Should execute successfully
            assert result.returncode == 0

            # Should show help
            assert "Usage:" in result.stdout
            assert "hidden-labels" in result.stdout

        finally:
            # Clean up
            if os.path.exists(tmp_db_path):
                os.unlink(tmp_db_path)


class TestHiddenLabelsCLIIntegration:
    """Test integration of hidden-labels command with other CLI features."""

    def test_hidden_labels_command_in_main_cli(self):
        """Test that the hidden-labels command is properly registered in the main CLI."""
        from fincli.cli import cli

        # Get the CLI commands
        commands = cli.commands

        # Should have the hidden-labels command
        assert "hidden-labels" in commands

        # Should be callable
        assert callable(commands["hidden-labels"].callback)

    def test_hidden_labels_command_click_commands_list(self):
        """Test that hidden-labels is in the click_commands list for proper routing."""
        # This tests the internal routing logic in the main() function
        # The command should be properly routed through Click
        # We can't easily test the main() function directly, but we can verify
        # that the command exists in the CLI structure
        from fincli.cli import cli, main

        assert "hidden-labels" in cli.commands

    def test_hidden_labels_command_consistency_with_verbose_flag(self):
        """Test that the hidden-labels command output is consistent with verbose flag behavior."""
        # Mock the get_hidden_labels_info function
        with patch("fincli.utils.get_hidden_labels_info") as mock_get_info:
            mock_get_info.return_value = {
                "authority:full": "Task authority level (full = fin-cli controls both definition and status)",
                "mod:*": "Task modification timestamp (when task was last modified)",
            }

            # Call the command function directly (bypassing Click argument parsing)
            import io
            import sys

            from fincli.cli import hidden_labels_command

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            try:
                # Call the function directly without Click argument parsing
                hidden_labels_command.callback()
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout

            # Verify that the descriptions match what users would see
            assert "authority:full" in output
            assert "mod:*" in output
            assert "Task authority level" in output
            assert "Task modification timestamp" in output
