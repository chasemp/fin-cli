"""
Safe tests for the editor functionality using example text files and transforms.
These tests ensure the editor logic works correctly without opening actual editors.
"""

import os
import tempfile
from datetime import date, datetime, timedelta

import pytest

from fincli.db import DatabaseManager
from fincli.editor import EditorManager
from fincli.tasks import TaskManager


class TestEditorSafe:
    """Test editor functionality safely without opening external editors."""

    def test_create_edit_file_content(self, temp_db_path):
        """Test creating edit file content without opening editor."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add some test tasks with labels to ensure they're included
        task_manager.add_task("Task 1", labels=["work"])
        task_manager.add_task("Task 2", labels=["personal"])

        # Mark one as completed
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET completed_at = ? WHERE content = ?",
                (datetime.now().isoformat(), "Task 2"),
            )
            conn.commit()

        # Get tasks for editing using label filtering to ensure we get all tasks
        tasks = editor_manager.get_tasks_for_editing(label="work")
        tasks.extend(editor_manager.get_tasks_for_editing(label="personal"))

        # Create file content
        content = editor_manager.create_edit_file_content(tasks)

        # Verify content structure
        lines = content.splitlines()
        assert lines[0] == "# Fin Tasks - Edit and save to update completion status"
        assert lines[1] == "# Changes tracked:"
        assert (
            lines[2] == "#   • Checkbox changes ([ ] ↔ [x]) - mark complete/incomplete"
        )
        assert lines[3] == "#   • Content changes - reword tasks (keeps same task ID)"
        assert lines[4] == "#   • New tasks - add lines without #ref:task_XXX"
        assert lines[5] == "#   • Task deletion - remove lines to delete tasks"
        assert lines[6] == "# Lines starting with # are ignored"
        assert (
            lines[7]
            == "# DO NOT modify the #ref:task_XXX part - it's used to track changes"
        )
        assert lines[8] == ""

        # Check that both tasks are in the content with reference IDs
        content_str = "\n".join(lines)
        assert "Task 1" in content_str
        assert "Task 2" in content_str
        assert "#ref:task_" in content_str

    def test_parse_edited_content_no_changes(self, temp_db_path):
        """Test parsing edited content with no changes."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add a task with a label to ensure it's included
        task_manager.add_task("Test task", labels=["test"])

        # Create original content using label filtering
        tasks = editor_manager.get_tasks_for_editing(label="test")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Parse the same content (no changes)
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(original_content)

        assert completed_count == 0
        assert reopened_count == 0
        assert new_tasks_count == 0

    def test_parse_edited_content_complete_task(self, temp_db_path):
        """Test parsing edited content with a task marked as completed."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add a task with a label to ensure it's included
        task_id = task_manager.add_task("Test task", labels=["test"])

        # Create original content using label filtering
        tasks = editor_manager.get_tasks_for_editing(label="test")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Modify content to mark task as completed
        modified_lines = []
        for line in original_content.splitlines():
            if "Test task" in line and "[ ]" in line:
                # Replace [ ] with [x] to mark as completed
                line = line.replace("[ ]", "[x]")
            modified_lines.append(line)

        modified_content = "\n".join(modified_lines)

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        assert completed_count == 1
        assert reopened_count == 0
        assert new_tasks_count == 0

        # Verify the task was actually marked as completed in the database
        updated_task = task_manager.get_task(task_id)
        assert updated_task["completed_at"] is not None

    def test_parse_edited_content_reopen_task(self, temp_db_path):
        """Test parsing edited content with a completed task reopened."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add a task with a label and mark it as completed
        task_id = task_manager.add_task("Test task", labels=["test"])
        task_manager.update_task_completion(task_id, True)

        # Create original content using label filtering
        tasks = editor_manager.get_tasks_for_editing(label="test")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Modify content to mark task as open again
        modified_lines = []
        for line in original_content.splitlines():
            if "Test task" in line and "[x]" in line:
                # Replace [x] with [ ] to mark as open
                line = line.replace("[x]", "[ ]")
            modified_lines.append(line)

        modified_content = "\n".join(modified_lines)

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        assert completed_count == 0
        assert reopened_count == 1
        assert new_tasks_count == 0

        # Verify the task was actually reopened in the database
        updated_task = task_manager.get_task(task_id)
        assert updated_task["completed_at"] is None

    def test_parse_edited_content_add_new_task(self, temp_db_path):
        """Test parsing edited content with a new task added."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add an existing task
        task_manager.add_task("Existing task", labels=["test"])

        # Create original content
        tasks = editor_manager.get_tasks_for_editing(label="test")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Add a new task line (without reference ID)
        new_task_line = "[ ] 2024-01-01 10:00  New task  #test"
        modified_content = original_content + "\n" + new_task_line

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        assert completed_count == 0
        assert reopened_count == 0
        assert new_tasks_count == 1

        # Verify the new task was actually added to the database
        all_tasks = task_manager.list_tasks(include_completed=True)
        new_tasks = [t for t in all_tasks if t["content"] == "New task"]
        assert len(new_tasks) == 1

    def test_parse_edited_content_add_new_task_without_timestamp(self, temp_db_path):
        """Test parsing edited content with a new task added without timestamp."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add an existing task
        task_manager.add_task("Existing task", labels=["test"])

        # Create original content
        tasks = editor_manager.get_tasks_for_editing(label="test")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Add a new task line without timestamp (new format)
        new_task_line = "[] New task without timestamp  #test"
        modified_content = original_content + "\n" + new_task_line

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        assert completed_count == 0
        assert reopened_count == 0
        assert new_tasks_count == 1

        # Verify the new task was actually added to the database with timestamp
        all_tasks = task_manager.list_tasks(include_completed=True)
        new_tasks = [
            t for t in all_tasks if t["content"] == "New task without timestamp"
        ]
        assert len(new_tasks) == 1

        # Verify the task has a timestamp (should be automatically added)
        new_task = new_tasks[0]
        assert new_task["created_at"] is not None
        assert new_task["created_at"] != ""

    def test_parse_edited_content_add_new_task_with_labels(self, temp_db_path):
        """Test parsing edited content with a new task added without timestamp but with labels."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add an existing task
        task_manager.add_task("Existing task", labels=["test"])

        # Create original content
        tasks = editor_manager.get_tasks_for_editing(label="test")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Add a new task line without timestamp but with labels
        new_task_line = "[] New task with labels  #work #urgent"
        modified_content = original_content + "\n" + new_task_line

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        assert completed_count == 0
        assert reopened_count == 0
        assert new_tasks_count == 1

        # Verify the new task was actually added to the database with labels
        all_tasks = task_manager.list_tasks(include_completed=True)
        new_tasks = [t for t in all_tasks if t["content"] == "New task with labels"]
        assert len(new_tasks) == 1

        # Verify the task has labels and timestamp
        new_task = new_tasks[0]
        assert new_task["created_at"] is not None
        assert new_task["created_at"] != ""
        assert "work" in new_task["labels"]
        assert "urgent" in new_task["labels"]

    def test_parse_edited_content_add_new_task_with_space_format(self, temp_db_path):
        """Test parsing edited content with a new task using [ ] format."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add an existing task
        task_manager.add_task("Existing task", labels=["test"])

        # Create original content
        tasks = editor_manager.get_tasks_for_editing(label="test")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Add a new task line with [ ] format (with space)
        new_task_line = "[ ] New task with space format  #test"
        modified_content = original_content + "\n" + new_task_line

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        assert completed_count == 0
        assert reopened_count == 0
        assert new_tasks_count == 1

        # Verify the new task was actually added to the database
        all_tasks = task_manager.list_tasks(include_completed=True)
        new_tasks = [
            t for t in all_tasks if t["content"] == "New task with space format"
        ]
        assert len(new_tasks) == 1

        # Verify the task has a timestamp
        new_task = new_tasks[0]
        assert new_task["created_at"] is not None
        assert new_task["created_at"] != ""

    def test_parse_task_line_new_format(self, temp_db_path):
        """Test that parse_task_line correctly handles new task formats without timestamps."""
        db_manager = DatabaseManager(temp_db_path)
        editor_manager = EditorManager(db_manager)

        # Test parsing new task without timestamp
        result = editor_manager.parse_task_line("[] New task without timestamp")
        assert result is not None
        assert result["content"] == "New task without timestamp"
        assert result["status"] == "[ ]"  # Should be normalized
        assert result["timestamp"] == ""  # No timestamp
        assert result["task_id"] is None  # New task
        assert result["is_completed"] is False

        # Test parsing new task with labels
        result = editor_manager.parse_task_line(
            "[] New task with labels  #work #urgent"
        )
        assert result is not None
        assert result["content"] == "New task with labels"
        assert result["status"] == "[ ]"  # Should be normalized
        assert result["timestamp"] == ""  # No timestamp
        assert result["task_id"] is None  # New task
        assert result["is_completed"] is False
        assert "work" in result["labels"]
        assert "urgent" in result["labels"]

        # Test parsing new task with space format
        result = editor_manager.parse_task_line("[ ] New task with space format")
        assert result is not None
        assert result["content"] == "New task with space format"
        assert result["status"] == "[ ]"
        assert result["timestamp"] == ""  # No timestamp
        assert result["task_id"] is None  # New task
        assert result["is_completed"] is False

        # Test that existing format still works
        result = editor_manager.parse_task_line(
            "[ ] 2024-01-01 10:00  Existing task  #ref:task_123"
        )
        assert result is not None
        assert result["content"] == "Existing task"
        assert result["status"] == "[ ]"
        assert result["timestamp"] == "2024-01-01 10:00"
        assert result["task_id"] == 123
        assert result["is_completed"] is False

    def test_parse_edited_content_reword_task(self, temp_db_path):
        """Test parsing edited content with a task reworded."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add a task
        task_id = task_manager.add_task("Original task", labels=["test"])

        # Create original content
        tasks = editor_manager.get_tasks_for_editing(label="test")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Modify content to reword the task (but keep the reference ID)
        modified_lines = []
        for line in original_content.splitlines():
            if "Original task" in line:
                # Replace the content but keep the reference ID
                line = line.replace("Original task", "Reworded task")
            modified_lines.append(line)

        modified_content = "\n".join(modified_lines)

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        # Should not create any changes since we only track completion status
        assert completed_count == 0
        assert reopened_count == 0
        assert new_tasks_count == 0

        # The task should still exist with original content (rewording is not tracked)
        updated_task = task_manager.get_task(task_id)
        assert updated_task["content"] == "Original task"

    def test_parse_edited_content_multiple_changes(self, temp_db_path):
        """Test parsing edited content with multiple changes."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add multiple tasks with labels
        task1_id = task_manager.add_task("Task 1", labels=["work"])
        task2_id = task_manager.add_task("Task 2", labels=["personal"])
        task3_id = task_manager.add_task("Task 3", labels=["urgent"])

        # Mark one as completed initially
        task_manager.update_task_completion(task2_id, True)

        # Create original content using label filtering to get all tasks
        all_tasks = []
        for label in ["work", "personal", "urgent"]:
            tasks = editor_manager.get_tasks_for_editing(label=label)
            all_tasks.extend(tasks)
        original_content = editor_manager.create_edit_file_content(all_tasks)

        # Add a new task line
        new_task_line = "[ ] 2024-01-01 10:00  New task  #work"

        # Modify content: complete task1, reopen task2, leave task3 unchanged, add new task
        modified_lines = []
        for line in original_content.splitlines():
            if "Task 1" in line and "[ ]" in line:
                line = line.replace("[ ]", "[x]")
            elif "Task 2" in line and "[x]" in line:
                line = line.replace("[x]", "[ ]")
            modified_lines.append(line)

        modified_content = "\n".join(modified_lines) + "\n" + new_task_line

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        assert completed_count == 1  # Task 1 completed
        assert reopened_count == 1  # Task 2 reopened
        assert new_tasks_count == 1  # New task added

        # Verify the changes in the database
        task1 = task_manager.get_task(task1_id)
        task2 = task_manager.get_task(task2_id)
        task3 = task_manager.get_task(task3_id)

        assert task1["completed_at"] is not None  # Completed
        assert task2["completed_at"] is None  # Reopened
        assert task3["completed_at"] is None  # Unchanged

        # Verify new task was added
        all_tasks = task_manager.list_tasks(include_completed=True)
        new_tasks = [t for t in all_tasks if t["content"] == "New task"]
        assert len(new_tasks) == 1

    def test_parse_edited_content_ignores_invalid_lines(self, temp_db_path):
        """Test that invalid lines are ignored when parsing."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add a task with a label
        task_manager.add_task("Test task", labels=["test"])

        # Get the actual task to get its timestamp and reference
        tasks = editor_manager.get_tasks_for_editing(label="test")
        assert len(tasks) == 1
        task = tasks[0]

        # Extract the timestamp from the task
        created_dt = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00"))
        timestamp = created_dt.strftime("%Y-%m-%d %H:%M")
        reference = editor_manager._generate_task_id(task["id"])

        # Create content with invalid lines using the actual timestamp and reference
        invalid_content = f"""# Fin Tasks - Edit and save to update completion status
# Only checkbox changes ([ ] ↔ [x]) are tracked
# Lines starting with # are ignored

[ ] {timestamp}  Test task  #test  #ref:{reference}

# This is a comment line
Invalid line without proper format
[x] {timestamp}  Test task  #test  #ref:{reference}
"""

        # Parse the content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(invalid_content)

        # Should only count the valid task line changes
        assert completed_count == 1
        assert reopened_count == 0
        assert new_tasks_count == 0

    def test_editor_safety_flag(self, temp_db_path):
        """Test that the editor safety flag prevents multiple editor openings."""
        db_manager = DatabaseManager(temp_db_path)
        editor_manager = EditorManager(db_manager)

        # Add a task so the editor has something to work with
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Test task", labels=["test"])

        # Test the safety flag directly by setting it manually
        editor_manager._editor_opened = True

        # Second call should raise an error
        with pytest.raises(RuntimeError, match="Editor has already been opened"):
            editor_manager.edit_tasks(label="test")

    def test_simulate_edit_with_content(self, temp_db_path):
        """Test the simulate_edit_with_content method."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add a task with a label
        task_manager.add_task("Test task", labels=["test"])

        # Create original and modified content
        tasks = editor_manager.get_tasks_for_editing(label="test")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Modify content to mark task as completed
        modified_content = original_content.replace("[ ]", "[x]")

        # Simulate the edit
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.simulate_edit_with_content(
            original_content, modified_content
        )

        assert completed_count == 1
        assert reopened_count == 0
        assert new_tasks_count == 0

    def test_get_tasks_for_editing_label_filter(self, temp_db_path):
        """Test getting tasks for editing with label filtering."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add tasks with different labels
        task_manager.add_task("Work task", labels=["work"])
        task_manager.add_task("Personal task", labels=["personal"])
        task_manager.add_task("Another work task", labels=["work"])

        # Test filtering by label
        work_tasks = editor_manager.get_tasks_for_editing(label="work")
        assert len(work_tasks) == 2
        assert all("work" in task["labels"] for task in work_tasks)

        personal_tasks = editor_manager.get_tasks_for_editing(label="personal")
        assert len(personal_tasks) == 1
        assert personal_tasks[0]["content"] == "Personal task"

    def test_get_tasks_for_editing_date_filter(self, temp_db_path):
        """Test getting tasks for editing with date filtering."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add tasks
        task_manager.add_task("Today's task", labels=["today"])
        task_manager.add_task("Yesterday's task", labels=["yesterday"])

        # Mark yesterday's task as completed with yesterday's date
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            yesterday = date.today() - timedelta(days=1)
            cursor.execute(
                "UPDATE tasks SET completed_at = ? WHERE content = ?",
                (yesterday.strftime("%Y-%m-%d 12:00:00"), "Yesterday's task"),
            )
            conn.commit()

        # Test filtering by today's date
        today_tasks = editor_manager.get_tasks_for_editing(
            target_date=date.today().strftime("%Y-%m-%d")
        )
        assert len(today_tasks) == 1
        assert today_tasks[0]["content"] == "Today's task"

        # Test filtering by yesterday's date
        yesterday_tasks = editor_manager.get_tasks_for_editing(
            target_date=(date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        )
        assert len(yesterday_tasks) == 1
        assert yesterday_tasks[0]["content"] == "Yesterday's task"

    # Additional comprehensive text transform test cases
    def test_text_transform_add_new_task_simple(self, temp_db_path):
        """Test adding a new task with simple text transform."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Start with empty content
        original_content = """# Fin Tasks - Edit and save to update completion status
# Only checkbox changes ([ ] ↔ [x]) are tracked
# Lines starting with # are ignored
# Add new tasks by adding lines without #ref:task_XXX
# DO NOT modify the #ref:task_XXX part - it's used to track changes

"""

        # Add a new task line
        modified_content = original_content + "[ ] 2024-01-01 10:00  My new task  #work"

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        assert completed_count == 0
        assert reopened_count == 0
        assert new_tasks_count == 1

        # Verify the new task was added
        all_tasks = task_manager.list_tasks(include_completed=True)
        new_tasks = [t for t in all_tasks if t["content"] == "My new task"]
        assert len(new_tasks) == 1
        assert "work" in new_tasks[0]["labels"]

    def test_text_transform_complete_task_simple(self, temp_db_path):
        """Test completing a task with simple text transform."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add a task
        task_id = task_manager.add_task("My task", labels=["work"])

        # Create content with the task
        tasks = editor_manager.get_tasks_for_editing(label="work")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Transform: [ ] my task => [x] my task
        modified_content = original_content.replace("[ ]", "[x]")

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        assert completed_count == 1
        assert reopened_count == 0
        assert new_tasks_count == 0

        # Verify the task was completed
        updated_task = task_manager.get_task(task_id)
        assert updated_task["completed_at"] is not None

    def test_text_transform_reopen_task_simple(self, temp_db_path):
        """Test reopening a task with simple text transform."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add and complete a task
        task_id = task_manager.add_task("My task", labels=["work"])
        task_manager.update_task_completion(task_id, True)

        # Create content with the completed task
        tasks = editor_manager.get_tasks_for_editing(label="work")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Transform: [x] my task => [ ] my task
        modified_content = original_content.replace("[x]", "[ ]")

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        assert completed_count == 0
        assert reopened_count == 1
        assert new_tasks_count == 0

        # Verify the task was reopened
        updated_task = task_manager.get_task(task_id)
        assert updated_task["completed_at"] is None

    def test_text_transform_reword_task_simple(self, temp_db_path):
        """Test rewording a task with simple text transform."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add a task
        task_id = task_manager.add_task("My task", labels=["work"])

        # Create content with the task
        tasks = editor_manager.get_tasks_for_editing(label="work")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Transform: [ ] my task => [ ] this is the same task but reworded
        modified_content = original_content.replace(
            "My task", "This is the same task but reworded"
        )

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        # Should not create any changes since we only track completion status
        assert completed_count == 0
        assert reopened_count == 0
        assert new_tasks_count == 0

        # The task should still exist with original content (rewording is not tracked)
        updated_task = task_manager.get_task(task_id)
        assert updated_task["content"] == "My task"

    def test_text_transform_complex_scenario(self, temp_db_path):
        """Test a complex scenario with multiple text transforms."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add multiple tasks
        task1_id = task_manager.add_task("Task 1", labels=["work"])
        task2_id = task_manager.add_task("Task 2", labels=["personal"])
        task3_id = task_manager.add_task("Task 3", labels=["urgent"])

        # Mark one as completed initially
        task_manager.update_task_completion(task2_id, True)

        # Create original content
        all_tasks = []
        for label in ["work", "personal", "urgent"]:
            tasks = editor_manager.get_tasks_for_editing(label=label)
            all_tasks.extend(tasks)
        original_content = editor_manager.create_edit_file_content(all_tasks)

        # Apply multiple text transforms:
        # 1. Complete task 1: [ ] Task 1 => [x] Task 1
        # 2. Reopen task 2: [x] Task 2 => [ ] Task 2
        # 3. Add new task: Add "[ ] 2024-01-01 10:00  New task  #work"
        # 4. Reword task 3: [ ] Task 3 => [ ] This is task 3 reworded
        modified_lines = []
        for line in original_content.splitlines():
            if "Task 1" in line and "[ ]" in line:
                line = line.replace("[ ]", "[x]")
            elif "Task 2" in line and "[x]" in line:
                line = line.replace("[x]", "[ ]")
            elif "Task 3" in line:
                line = line.replace("Task 3", "This is task 3 reworded")
            modified_lines.append(line)

        # Add new task
        modified_content = (
            "\n".join(modified_lines) + "\n[ ] 2024-01-01 10:00  New task  #work"
        )

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        assert completed_count == 1  # Task 1 completed
        assert reopened_count == 1  # Task 2 reopened
        assert new_tasks_count == 1  # New task added

        # Verify the changes in the database
        task1 = task_manager.get_task(task1_id)
        task2 = task_manager.get_task(task2_id)
        task3 = task_manager.get_task(task3_id)

        assert task1["completed_at"] is not None  # Completed
        assert task2["completed_at"] is None  # Reopened
        assert task3["completed_at"] is None  # Unchanged (rewording not tracked)
        assert task3["content"] == "Task 3"  # Content unchanged

        # Verify new task was added
        all_tasks = task_manager.list_tasks(include_completed=True)
        new_tasks = [t for t in all_tasks if t["content"] == "New task"]
        assert len(new_tasks) == 1

    def test_text_transform_edge_cases(self, temp_db_path):
        """Test edge cases with text transforms."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add a task
        task_id = task_manager.add_task("Test task", labels=["work"])

        # Create content
        tasks = editor_manager.get_tasks_for_editing(label="work")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Test various edge cases
        edge_cases = [
            # Empty content
            "",
            # Only comments
            "# This is a comment\n# Another comment",
            # Invalid task format
            "[invalid] 2024-01-01 10:00  Invalid task",
            # Task with empty content (this will be treated as a new task)
            "[ ] 2024-01-01 10:00    #work",
            # Task with special characters (this will be treated as a new task)
            "[ ] 2024-01-01 10:00  Task with special chars: !@#$%^&*()  #work",
        ]

        # Expected results for each edge case
        expected_results = [
            (0, 0, 0),  # Empty content
            (0, 0, 0),  # Only comments
            (0, 0, 0),  # Invalid task format
            (0, 0, 1),  # Task with empty content (treated as new task)
            (0, 0, 1),  # Task with special characters (treated as new task)
        ]

        for i, edge_case in enumerate(edge_cases):
            # Parse edge case content
            (
                completed_count,
                reopened_count,
                new_tasks_count,
                content_modified_count,
                deleted_count,
            ) = editor_manager.parse_edited_content(edge_case)

            expected_completed, expected_reopened, expected_new = expected_results[i]

            # Check expected results
            assert (
                completed_count == expected_completed
            ), f"Edge case {i} failed: expected {expected_completed} completed, got {completed_count}"
            assert (
                reopened_count == expected_reopened
            ), f"Edge case {i} failed: expected {expected_reopened} reopened, got {reopened_count}"
            assert (
                new_tasks_count == expected_new
            ), f"Edge case {i} failed: expected {expected_new} new tasks, got {new_tasks_count}"

    def test_text_transform_preserves_reference_ids(self, temp_db_path):
        """Test that reference IDs are preserved during text transforms."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add a task
        task_id = task_manager.add_task("Test task", labels=["work"])

        # Create content
        tasks = editor_manager.get_tasks_for_editing(label="work")
        original_content = editor_manager.create_edit_file_content(tasks)

        # Verify reference ID is present
        assert "#ref:task_" in original_content

        # Apply text transform (complete the task)
        modified_content = original_content.replace("[ ]", "[x]")

        # Verify reference ID is still present
        assert "#ref:task_" in modified_content

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        assert completed_count == 1
        assert reopened_count == 0
        assert new_tasks_count == 0

        # Verify the task was completed
        updated_task = task_manager.get_task(task_id)
        assert updated_task["completed_at"] is not None

    def test_enhanced_summary_functionality(self, temp_db_path):
        """Test the enhanced summary functionality with detailed change reporting."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add multiple tasks with different states
        task1_id = task_manager.add_task("Task to complete", labels=["work"])
        task2_id = task_manager.add_task("Task to reopen", labels=["personal"])
        task3_id = task_manager.add_task("Task to leave unchanged", labels=["work"])

        # Mark one as completed initially
        task_manager.update_task_completion(task2_id, True)

        # Get original state - need to get all tasks to include the personal task
        original_tasks = []
        for label in ["work", "personal"]:
            tasks = editor_manager.get_tasks_for_editing(label=label)
            original_tasks.extend(tasks)
        original_completed = [t for t in original_tasks if t.get("completed_at")]
        original_open = [t for t in original_tasks if not t.get("completed_at")]

        # Create content for editing
        all_tasks = []
        for label in ["work", "personal"]:
            tasks = editor_manager.get_tasks_for_editing(label=label)
            all_tasks.extend(tasks)
        original_content = editor_manager.create_edit_file_content(all_tasks)

        # Simulate editor changes:
        # 1. Complete task1: [ ] Task to complete => [x] Task to complete
        # 2. Reopen task2: [x] Task to reopen => [ ] Task to reopen
        # 3. Add new task: Add "[ ] 2024-01-01 10:00  New task  #work"
        modified_lines = []
        for line in original_content.splitlines():
            if "Task to complete" in line and "[ ]" in line:
                line = line.replace("[ ]", "[x]")
            elif "Task to reopen" in line and "[x]" in line:
                line = line.replace("[x]", "[ ]")
            modified_lines.append(line)

        # Add new task
        modified_content = (
            "\n".join(modified_lines) + "\n[ ] 2024-01-01 10:00  New task  #work"
        )

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(modified_content)

        # Verify the changes were applied
        assert completed_count == 1  # Task to complete
        assert reopened_count == 1  # Task to reopen
        assert new_tasks_count == 1  # New task added

        # Get updated state - need to get all tasks to see the reopened one
        all_updated_tasks = []
        for label in ["work", "personal"]:
            tasks = editor_manager.get_tasks_for_editing(label=label)
            all_updated_tasks.extend(tasks)
        updated_completed = [t for t in all_updated_tasks if t.get("completed_at")]
        updated_open = [t for t in all_updated_tasks if not t.get("completed_at")]

        # Verify the specific changes
        # Check that task1 is now completed
        task1 = task_manager.get_task(task1_id)
        assert task1["completed_at"] is not None

        # Check that task2 is now reopened
        task2 = task_manager.get_task(task2_id)
        assert task2["completed_at"] is None

        # Check that task3 is unchanged
        task3 = task_manager.get_task(task3_id)
        assert task3["completed_at"] is None

        # Check that new task was added
        all_tasks = task_manager.list_tasks(include_completed=True)
        new_tasks = [t for t in all_tasks if t["content"] == "New task"]
        assert len(new_tasks) == 1
        assert "work" in new_tasks[0]["labels"]

        # Verify the summary data would be correct
        # Compare by task ID since objects are different instances
        original_completed_ids = {t["id"] for t in original_completed}
        newly_completed = [
            t for t in updated_completed if t["id"] not in original_completed_ids
        ]
        assert len(newly_completed) == 1
        assert newly_completed[0]["content"] == "Task to complete"

        # Note: reopened tasks would be in updated_open but were in original_completed
        # This is the logic for detecting reopened tasks
        newly_reopened = [t for t in updated_open if t["id"] in original_completed_ids]

        assert len(newly_reopened) == 1
        assert newly_reopened[0]["content"] == "Task to reopen"

    def test_text_transform_task_deletion(self, temp_db_path):
        """Test that removing tasks from the editor deletes them from the database."""
        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        editor_manager = EditorManager(db_manager)

        # Add tasks to delete
        task1_id = task_manager.add_task("Task to delete", labels=["work"])
        task2_id = task_manager.add_task("Task to keep", labels=["work"])
        task3_id = task_manager.add_task("Another task to delete", labels=["personal"])

        # Create original content
        all_tasks = []
        for label in ["work", "personal"]:
            tasks = editor_manager.get_tasks_for_editing(label=label)
            all_tasks.extend(tasks)
        original_content = editor_manager.create_edit_file_content(all_tasks)

        # Remove task1 and task3 from the content (simulate user deleting lines)
        modified_lines = []
        for line in original_content.splitlines():
            if "Task to delete" not in line and "Another task to delete" not in line:
                modified_lines.append(line)

        modified_content = "\n".join(modified_lines)

        # Parse the modified content
        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.parse_edited_content(
            modified_content, {task1_id, task2_id, task3_id}
        )

        # Verify the changes
        assert completed_count == 0
        assert reopened_count == 0
        assert new_tasks_count == 0
        assert deleted_count == 2  # task1 and task3 should be deleted

        # Verify that task1 and task3 were deleted
        deleted_task1 = task_manager.get_task(task1_id)
        deleted_task3 = task_manager.get_task(task3_id)
        assert deleted_task1 is None
        assert deleted_task3 is None

        # Verify that task2 still exists
        kept_task2 = task_manager.get_task(task2_id)
        assert kept_task2 is not None
        assert kept_task2["content"] == "Task to keep"
