"""
Tests for the fine command functionality
"""

import subprocess
import sys
from datetime import date, datetime, timedelta

import pytest

from fincli.cli import open_editor
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
        import tempfile, os
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
        assert result is not None
        assert result["status"] == "[ ]"
        assert result["timestamp"] == "2025-07-30 09:15"
        assert result["content"] == "Write unit tests"
        assert result["labels"] == ["testing"]
        assert result["is_completed"] is False

    def test_parse_task_line_completed(self):
        """Test parsing a completed task line."""
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False, dir="/tmp")
        tmp.close()
        db_path = tmp.name
        try:
            os.environ["FIN_DB_PATH"] = db_path
            from fincli.db import DatabaseManager
            db_manager = DatabaseManager()
            line = "[x] 2025-07-29 17:10  Fix bug in cron task runner  #automation"
            editor_manager = EditorManager(db_manager)
            result = editor_manager.parse_task_line(line)
            
            assert result is not None
            assert result["status"] == "[x]"
            assert result["timestamp"] == "2025-07-29 17:10"
            assert result["content"] == "Fix bug in cron task runner"
            assert result["labels"] == ["automation"]
            assert result["is_completed"] is True
        finally:
            os.unlink(db_path)
        assert result is not None
        assert result["status"] == "[x]"
        assert result["timestamp"] == "2025-07-29 17:10"
        assert result["content"] == "Fix bug in cron task runner"
        assert result["labels"] == ["automation"]
        assert result["is_completed"] is True

    def test_parse_task_line_no_labels(self):
        """Test parsing a task line without labels."""
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False, dir="/tmp")
        tmp.close()
        db_path = tmp.name
        try:
            os.environ["FIN_DB_PATH"] = db_path
            from fincli.db import DatabaseManager
            db_manager = DatabaseManager()
            line = "[ ] 2025-07-30 10:30  Simple task"
            editor_manager = EditorManager(db_manager)
            result = editor_manager.parse_task_line(line)
            
            assert result is not None
            assert result["content"] == "Simple task"
            assert result["labels"] == []
        finally:
            os.unlink(db_path)
        assert result is not None
        assert result["content"] == "Simple task"
        assert result["labels"] == []

    def test_parse_task_line_invalid(self):
        """Test parsing an invalid task line."""
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False, dir="/tmp")
        tmp.close()
        db_path = tmp.name
        try:
            os.environ["FIN_DB_PATH"] = db_path
            from fincli.db import DatabaseManager
            db_manager = DatabaseManager()
            line = "This is not a task line"
            editor_manager = EditorManager(db_manager)
            result = editor_manager.parse_task_line(line)
            
            assert result is None
        finally:
            os.unlink(db_path)
        assert result is None

    def test_find_matching_task(self, db_manager):
        """Test finding a matching task in the database."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)

    def test_fine_command_with_tasks(self, cli_runner):
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False, dir="/tmp")
        tmp.close()
        db_path = tmp.name
        try:
            os.environ["FIN_DB_PATH"] = db_path
            from fincli.db import DatabaseManager
            from fincli.tasks import TaskManager
            db_manager = DatabaseManager()
            task_manager = TaskManager(db_manager)
            task_manager.add_task("Test task", labels=["work"])
            pass
            del db_manager
            del task_manager
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
                    stdout = ""
                    stderr = ""
                return MockResult()
            import pytest
            monkeypatch = pytest.MonkeyPatch()
            monkeypatch.setattr("subprocess.run", mock_subprocess_run)
            result = cli_runner.invoke(open_editor, [])
            monkeypatch.undo()
            assert result.exit_code == 0
            assert "Opening tasks in editor..." in result.output
        finally:
            os.unlink(db_path)
