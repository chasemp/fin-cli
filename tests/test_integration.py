"""
Integration tests for Fin task tracking system
"""
import pytest
import subprocess
import sys
import sqlite3
import tempfile
import os
from pathlib import Path
from fin.database.manager import DatabaseManager


class TestIntegration:
    """Integration tests for the complete system."""
    
    def test_full_cli_to_database_flow(self, temp_db_path, monkeypatch):
        """Test complete flow from CLI to database storage."""
        # Set up environment
        monkeypatch.setenv('FIN_DB_PATH', temp_db_path)
        
        # Add task via CLI
        result = subprocess.run([
            sys.executable, '-m', 'fin.cli.main', 'add',
            'Integration test task',
            '--label', 'test',
            '--label', 'integration'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "✅ Task added: \"Integration test task\" [integration, test]" in result.stdout
        
        # Verify task in database
        db_manager = DatabaseManager(temp_db_path)
        tasks = db_manager.list_tasks()
        
        assert len(tasks) == 1
        task = tasks[0]
        assert task['content'] == "Integration test task"
        assert set(task['labels']) == {"test", "integration"}
        assert task['source'] == "cli"
    
    def test_multiple_cli_operations(self, temp_db_path, monkeypatch):
        """Test multiple CLI operations in sequence."""
        # Set up environment
        monkeypatch.setenv('FIN_DB_PATH', temp_db_path)
        
        # Add multiple tasks
        tasks_to_add = [
            ("First task", ["work"]),
            ("Second task", ["personal", "urgent"]),
            ("Third task", []),
        ]
        
        for content, labels in tasks_to_add:
            cmd = [sys.executable, '-m', 'fin.cli.main', 'add', content]
            for label in labels:
                cmd.extend(['--label', label])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            assert result.returncode == 0
        
        # Verify all tasks in database
        db_manager = DatabaseManager(temp_db_path)
        tasks = db_manager.list_tasks()
        
        assert len(tasks) == 3
        
        # Check that all tasks are present (order may vary due to same timestamps)
        task_contents = [task['content'] for task in tasks]
        assert "First task" in task_contents
        assert "Second task" in task_contents
        assert "Third task" in task_contents
    
    def test_cli_error_handling(self, temp_db_path, monkeypatch):
        """Test CLI error handling in integration."""
        # Set up environment
        monkeypatch.setenv('FIN_DB_PATH', temp_db_path)
        
        # Test missing argument for add command
        result = subprocess.run([
            sys.executable, '-m', 'fin.cli.main', 'add'
        ], capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "Missing argument" in result.stderr
        
        # Verify database is still accessible
        db_manager = DatabaseManager(temp_db_path)
        tasks = db_manager.list_tasks()
        assert len(tasks) == 0  # No tasks should be added
    
    def test_database_persistence_across_cli_calls(self, temp_db_path, monkeypatch):
        """Test that database persists data across CLI calls."""
        # Set up environment
        monkeypatch.setenv('FIN_DB_PATH', temp_db_path)
        
        # Add task via CLI
        subprocess.run([
            sys.executable, '-m', 'fin.cli.main', 'add',
            'Persistent task'
        ], capture_output=True, text=True)
        
        # Verify task exists
        db_manager = DatabaseManager(temp_db_path)
        tasks = db_manager.list_tasks()
        assert len(tasks) == 1
        assert tasks[0]['content'] == "Persistent task"
        
        # Add another task
        subprocess.run([
            sys.executable, '-m', 'fin.cli.main', 'add',
            'Another persistent task',
            '--label', 'work'
        ], capture_output=True, text=True)
        
        # Verify both tasks exist
        tasks = db_manager.list_tasks()
        assert len(tasks) == 2
        # Check that both tasks exist, regardless of order
        task_contents = [task['content'] for task in tasks]
        assert "Persistent task" in task_contents
        assert "Another persistent task" in task_contents
    
    def test_special_characters_integration(self, temp_db_path, monkeypatch):
        """Test special characters in task content."""
        # Set up environment
        monkeypatch.setenv('FIN_DB_PATH', temp_db_path)
        
        special_content = "Task with 'quotes', \"double quotes\", and special chars: @#$%^&*()"
        
        result = subprocess.run([
            sys.executable, '-m', 'fin.cli.main', 'add',
            special_content
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        # Verify in database
        db_manager = DatabaseManager(temp_db_path)
        tasks = db_manager.list_tasks()
        
        assert len(tasks) == 1
        assert tasks[0]['content'] == special_content
    
    def test_label_normalization_integration(self, temp_db_path, monkeypatch):
        """Test label normalization in integration."""
        # Set up environment
        monkeypatch.setenv('FIN_DB_PATH', temp_db_path)
        
        result = subprocess.run([
            sys.executable, '-m', 'fin.cli.main', 'add',
            'Task with mixed case labels',
            '--label', 'WORK',
            '--label', 'Urgent',
            '--label', '  test  '
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "✅ Task added: \"Task with mixed case labels\" [test, urgent, work]" in result.stdout
        
        # Verify in database
        db_manager = DatabaseManager(temp_db_path)
        tasks = db_manager.list_tasks()
        
        assert len(tasks) == 1
        assert set(tasks[0]['labels']) == {"work", "urgent", "test"}


class TestRealDatabase:
    """Tests using the real database location."""
    
    def test_real_database_creation(self, monkeypatch):
        """Test that real database is created in ~/.fin/."""
        # Use a temporary home directory
        with tempfile.TemporaryDirectory() as tmp_home:
            monkeypatch.setenv('HOME', tmp_home)
            
            # Create database manager (should create ~/.fin/tasks.db)
            db_manager = DatabaseManager()
            
            # Verify directory and file exist
            fin_dir = Path(tmp_home) / ".fin"
            db_path = fin_dir / "tasks.db"
            
            assert fin_dir.exists()
            assert db_path.exists()
            
            # Add a task
            task_id = db_manager.add_task("Real database test")
            
            # Verify task was added
            task = db_manager.get_task(task_id)
            assert task is not None
            assert task['content'] == "Real database test"
    
    def test_real_database_persistence(self, monkeypatch):
        """Test that real database persists data."""
        # Use a temporary home directory
        with tempfile.TemporaryDirectory() as tmp_home:
            monkeypatch.setenv('HOME', tmp_home)
            
            # Create first manager and add task
            manager1 = DatabaseManager()
            task_id = manager1.add_task("Persistent real task")
            
            # Create second manager and verify task exists
            manager2 = DatabaseManager()
            task = manager2.get_task(task_id)
            
            assert task is not None
            assert task['content'] == "Persistent real task" 