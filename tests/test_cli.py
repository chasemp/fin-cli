"""
CLI tests for Fin task tracking system
"""
import pytest
import subprocess
import sys
from pathlib import Path
from fin.cli.main import main
from fin.cli.legacy import legacy_main


class TestCLI:
    """Test CLI functionality."""
    
    def test_cli_help(self, cli_runner):
        """Test CLI help output."""
        result = cli_runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert "Fin - A lightweight task tracking system" in result.output
        assert "Manage your local task database" in result.output
        assert "add" in result.output
        assert "fins" in result.output
    
    def test_cli_add_task_basic(self, cli_runner, temp_db_path, monkeypatch):
        """Test adding a basic task via CLI."""
        # Mock the database path
        monkeypatch.setattr('fin.database.manager.DatabaseManager.__init__', 
                           lambda self, db_path=None: self._init_mock_db(temp_db_path))
        
        result = cli_runner.invoke(main, ['add', 'Test task content'])
        
        assert result.exit_code == 0
        assert "✅ Task added: \"Test task content\"" in result.output
    
    def test_cli_add_task_with_labels(self, cli_runner, temp_db_path, monkeypatch):
        """Test adding a task with labels via CLI."""
        # Mock the database path
        monkeypatch.setattr('fin.database.manager.DatabaseManager.__init__', 
                           lambda self, db_path=None: self._init_mock_db(temp_db_path))
        
        result = cli_runner.invoke(main, [
            'add', 'Test task with labels',
            '--label', 'work',
            '--label', 'urgent'
        ])
        
        assert result.exit_code == 0
        assert "✅ Task added: \"Test task with labels\" [urgent, work]" in result.output
    
    def test_cli_add_task_with_source(self, cli_runner, temp_db_path, monkeypatch):
        """Test adding a task with custom source via CLI."""
        # Mock the database path
        monkeypatch.setattr('fin.database.manager.DatabaseManager.__init__', 
                           lambda self, db_path=None: self._init_mock_db(temp_db_path))
        
        result = cli_runner.invoke(main, [
            'add', 'Test task with source',
            '--source', 'test'
        ])
        
        assert result.exit_code == 0
        assert "✅ Task added: \"Test task with source\"" in result.output
    
    def test_cli_missing_content(self, cli_runner):
        """Test CLI with missing content argument."""
        result = cli_runner.invoke(main, ['add'])
        
        assert result.exit_code != 0
        assert "Missing argument" in result.output
    
    def test_cli_empty_content(self, cli_runner):
        """Test CLI with empty content."""
        result = cli_runner.invoke(main, ['add', ''])
        
        assert result.exit_code == 0
        assert "✅ Task added: \"\"" in result.output
    
    def test_cli_special_characters(self, cli_runner, temp_db_path, monkeypatch):
        """Test CLI with special characters in content."""
        # Mock the database path
        monkeypatch.setattr('fin.database.manager.DatabaseManager.__init__', 
                           lambda self, db_path=None: self._init_mock_db(temp_db_path))
        
        special_content = "Task with 'quotes', \"double quotes\", and special chars: @#$%^&*()"
        result = cli_runner.invoke(main, ['add', special_content])
        
        assert result.exit_code == 0
        assert f"✅ Task added: \"{special_content}\"" in result.output
    
    def test_cli_multiple_labels(self, cli_runner, temp_db_path, monkeypatch):
        """Test CLI with multiple label arguments."""
        # Mock the database path
        monkeypatch.setattr('fin.database.manager.DatabaseManager.__init__', 
                           lambda self, db_path=None: self._init_mock_db(temp_db_path))
        
        result = cli_runner.invoke(main, [
            'add', 'Complex task',
            '--label', 'work',
            '--label', 'urgent',
            '--label', 'personal'
        ])
        
        assert result.exit_code == 0
        assert "✅ Task added: \"Complex task\" [personal, urgent, work]" in result.output
    
    def test_cli_labels_normalization(self, cli_runner, temp_db_path, monkeypatch):
        """Test that CLI labels are normalized."""
        # Mock the database path
        monkeypatch.setattr('fin.database.manager.DatabaseManager.__init__', 
                           lambda self, db_path=None: self._init_mock_db(temp_db_path))
        
        result = cli_runner.invoke(main, [
            'add', 'Task with mixed case labels',
            '--label', 'WORK',
            '--label', 'Urgent',
            '--label', '  test  '
        ])
        
        assert result.exit_code == 0
        assert "✅ Task added: \"Task with mixed case labels\" [test, urgent, work]" in result.output
    
    def test_cli_empty_labels(self, cli_runner, temp_db_path, monkeypatch):
        """Test CLI with empty labels."""
        # Mock the database path
        monkeypatch.setattr('fin.database.manager.DatabaseManager.__init__', 
                           lambda self, db_path=None: self._init_mock_db(temp_db_path))
        
        result = cli_runner.invoke(main, [
            'add', 'Task with empty labels',
            '--label', '',
            '--label', '  ',
            '--label', 'valid'
        ])
        
        assert result.exit_code == 0
        assert "✅ Task added: \"Task with empty labels\" [valid]" in result.output


class TestCLIExecution:
    """Test CLI execution via subprocess."""
    
    def test_cli_execution_basic(self, temp_db_path, monkeypatch):
        """Test CLI execution via subprocess."""
        # Set up temporary database
        monkeypatch.setenv('FIN_DB_PATH', temp_db_path)
        
        result = subprocess.run([
            sys.executable, '-m', 'fin.cli.main', 'add',
            'Test task via subprocess'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "✅ Task added: \"Test task via subprocess\"" in result.stdout
    
    def test_cli_execution_with_labels(self, temp_db_path, monkeypatch):
        """Test CLI execution with labels via subprocess."""
        # Set up temporary database
        monkeypatch.setenv('FIN_DB_PATH', temp_db_path)
        
        result = subprocess.run([
            sys.executable, '-m', 'fin.cli.main', 'add',
            'Test task with labels',
            '--label', 'work',
            '--label', 'urgent'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "✅ Task added: \"Test task with labels\" [urgent, work]" in result.stdout
    
    def test_cli_execution_error_handling(self, temp_db_path, monkeypatch):
        """Test CLI error handling via subprocess."""
        # Set up temporary database
        monkeypatch.setenv('FIN_DB_PATH', temp_db_path)
        
        # Test with missing argument for add command
        result = subprocess.run([
            sys.executable, '-m', 'fin.cli.main', 'add'
        ], capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "Missing argument" in result.stderr
    
    def test_cli_execution_help(self, temp_db_path, monkeypatch):
        """Test CLI help via subprocess."""
        # Set up temporary database
        monkeypatch.setenv('FIN_DB_PATH', temp_db_path)
        
        result = subprocess.run([
            sys.executable, '-m', 'fin.cli.main',
            '--help'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Fin - A lightweight task tracking system" in result.stdout
        assert "Add a new task to your local task database" in result.stdout


class TestCLIOutput:
    """Test CLI output formatting."""
    
    def test_output_format_basic(self, cli_runner, temp_db_path, monkeypatch):
        """Test basic output format."""
        # Mock the database path
        monkeypatch.setattr('fin.database.manager.DatabaseManager.__init__', 
                           lambda self, db_path=None: self._init_mock_db(temp_db_path))
        
        result = cli_runner.invoke(main, ['add', 'Simple task'])
        
        assert result.exit_code == 0
        assert result.output.strip() == "✅ Task added: \"Simple task\""
    
    def test_output_format_with_labels(self, cli_runner, temp_db_path, monkeypatch):
        """Test output format with labels."""
        # Mock the database path
        monkeypatch.setattr('fin.database.manager.DatabaseManager.__init__', 
                           lambda self, db_path=None: self._init_mock_db(temp_db_path))
        
        result = cli_runner.invoke(main, ['add', 'Task with labels', '--label', 'work'])
        
        assert result.exit_code == 0
        assert result.output.strip() == "✅ Task added: \"Task with labels\" [work]"
    
    def test_output_format_multiple_labels(self, cli_runner, temp_db_path, monkeypatch):
        """Test output format with multiple labels."""
        # Mock the database path
        monkeypatch.setattr('fin.database.manager.DatabaseManager.__init__', 
                           lambda self, db_path=None: self._init_mock_db(temp_db_path))
        
        result = cli_runner.invoke(main, [
            'add', 'Task with multiple labels',
            '--label', 'work',
            '--label', 'urgent',
            '--label', 'personal'
        ])
        
        assert result.exit_code == 0
        assert result.output.strip() == "✅ Task added: \"Task with multiple labels\" [personal, urgent, work]" 