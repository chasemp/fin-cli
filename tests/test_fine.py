"""
Tests for the fine command functionality
"""
import pytest
import tempfile
import os
import subprocess
import sys
from datetime import datetime, date, timedelta
from fin.cli.commands import fine, get_editor, parse_task_line, find_matching_task, update_task_completion, filter_tasks_by_criteria
from fin.database.manager import DatabaseManager


class TestFineCommand:
    """Test fine command functionality."""
    
    def test_get_editor_with_env(self, monkeypatch):
        """Test getting editor from environment variable."""
        monkeypatch.setenv('EDITOR', 'vim')
        editor = get_editor()
        assert editor == 'vim'
    
    def test_get_editor_fallback(self, monkeypatch):
        """Test editor fallback when EDITOR not set."""
        monkeypatch.delenv('EDITOR', raising=False)
        editor = get_editor()
        assert editor in ['nano', 'vim', 'code']
    
    def test_parse_task_line_valid(self):
        """Test parsing a valid task line."""
        line = "[ ] 2025-07-30 09:15  Write unit tests  #testing"
        result = parse_task_line(line)
        
        assert result is not None
        assert result['status'] == "[ ]"
        assert result['timestamp'] == "2025-07-30 09:15"
        assert result['content'] == "Write unit tests"
        assert result['labels'] == ["testing"]
        assert result['is_completed'] is False
    
    def test_parse_task_line_completed(self):
        """Test parsing a completed task line."""
        line = "[x] 2025-07-29 17:10  Fix bug in cron task runner  #automation"
        result = parse_task_line(line)
        
        assert result is not None
        assert result['status'] == "[x]"
        assert result['timestamp'] == "2025-07-29 17:10"
        assert result['content'] == "Fix bug in cron task runner"
        assert result['labels'] == ["automation"]
        assert result['is_completed'] is True
    
    def test_parse_task_line_no_labels(self):
        """Test parsing a task line without labels."""
        line = "[ ] 2025-07-30 10:30  Simple task"
        result = parse_task_line(line)
        
        assert result is not None
        assert result['content'] == "Simple task"
        assert result['labels'] == []
    
    def test_parse_task_line_invalid(self):
        """Test parsing an invalid task line."""
        line = "This is not a task line"
        result = parse_task_line(line)
        
        assert result is None
    
    def test_find_matching_task(self, db_manager):
        """Test finding a matching task in the database."""
        # Add a task
        task_id = db_manager.add_task("Test matching task", labels=["work"])
        task = db_manager.get_task(task_id)
        
        # Create task info
        task_info = {
            'content': "Test matching task",
            'labels': ["work"],
            'timestamp': datetime.fromisoformat(task['created_at'].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M")
        }
        
        # Find matching task
        found_id = find_matching_task(task_info, db_manager)
        
        assert found_id == task_id
    
    def test_find_matching_task_not_found(self, db_manager):
        """Test finding a task that doesn't exist."""
        task_info = {
            'content': "Non-existent task",
            'labels': ["work"],
            'timestamp': "2025-07-30 10:00"
        }
        
        found_id = find_matching_task(task_info, db_manager)
        
        assert found_id is None
    
    def test_update_task_completion_complete(self, db_manager):
        """Test marking a task as completed."""
        # Add a task
        task_id = db_manager.add_task("Test completion task")
        
        # Mark as completed
        updated = update_task_completion(task_id, True, db_manager)
        
        assert updated is True
        
        # Verify in database
        task = db_manager.get_task(task_id)
        assert task['completed_at'] is not None
    
    def test_update_task_completion_reopen(self, db_manager):
        """Test reopening a completed task."""
        # Add a task and mark as completed
        task_id = db_manager.add_task("Test reopen task")
        
        # Mark as completed first
        update_task_completion(task_id, True, db_manager)
        
        # Then reopen
        updated = update_task_completion(task_id, False, db_manager)
        
        assert updated is True
        
        # Verify in database
        task = db_manager.get_task(task_id)
        assert task['completed_at'] is None
    
    def test_update_task_completion_no_change(self, db_manager):
        """Test updating task completion when no change is needed."""
        # Add a task
        task_id = db_manager.add_task("Test no change task")
        
        # Try to mark as open (it's already open)
        updated = update_task_completion(task_id, False, db_manager)
        
        assert updated is False
    
    def test_filter_tasks_by_label(self, db_manager):
        """Test filtering tasks by label."""
        # Add tasks with different labels
        db_manager.add_task("Work task", labels=["work"])
        db_manager.add_task("Personal task", labels=["personal"])
        db_manager.add_task("Work task 2", labels=["work", "urgent"])
        
        # Filter by work label
        filtered = filter_tasks_by_criteria(db_manager, label="work")
        
        assert len(filtered) == 2
        for task in filtered:
            assert "work" in [label.lower() for label in task['labels']]
    
    def test_filter_tasks_by_date(self, db_manager):
        """Test filtering tasks by date."""
        # Add tasks on different dates
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Add a task for today
        db_manager.add_task("Today's task")
        
        # Add a task for yesterday (by updating completed_at)
        task_id = db_manager.add_task("Yesterday's task")
        import sqlite3
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET completed_at = ? WHERE id = ?", 
                (yesterday.strftime("%Y-%m-%d 12:00:00"), task_id)
            )
            conn.commit()
        
        # Filter by today
        filtered = filter_tasks_by_criteria(db_manager, target_date=today.strftime("%Y-%m-%d"))
        
        assert len(filtered) == 1
        assert filtered[0]['content'] == "Today's task"
    
    def test_fine_command_help(self, cli_runner):
        """Test fine command help."""
        result = cli_runner.invoke(fine, ['--help'])
        
        assert result.exit_code == 0
        assert "Open tasks in your editor" in result.output
        assert "--label" in result.output
        assert "--date" in result.output
    
    def test_fine_command_no_tasks(self, cli_runner, temp_db_path, monkeypatch):
        """Test fine command with no tasks."""
        # Mock the database path
        monkeypatch.setattr('fin.database.manager.DatabaseManager.__init__', 
                           lambda self, db_path=None: self._init_mock_db(temp_db_path))
        
        result = cli_runner.invoke(fine, [])
        
        assert result.exit_code == 0
        assert "No tasks found matching your criteria" in result.output
    
    def test_fine_command_with_tasks(self, cli_runner, temp_db_path, monkeypatch):
        """Test fine command with tasks."""
        # Mock the database path
        monkeypatch.setattr('fin.database.manager.DatabaseManager.__init__', 
                           lambda self, db_path=None: self._init_mock_db(temp_db_path))
        
        # Add a task
        db_manager = DatabaseManager(temp_db_path)
        db_manager.add_task("Test task", labels=["work"])
        
        # Mock the editor to just return success
        def mock_subprocess_run(cmd, **kwargs):
            class MockResult:
                returncode = 0
            return MockResult()
        
        monkeypatch.setattr('subprocess.run', mock_subprocess_run)
        
        result = cli_runner.invoke(fine, [])
        
        assert result.exit_code == 0
        assert "Opening" in result.output
        assert "No changes detected" in result.output


 