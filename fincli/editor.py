"""
Editor module for FinCLI

Handles the fine command functionality for editing tasks in an external editor.
This module is designed to be safe and only trigger editor opening when explicitly requested.
"""

import hashlib
import os
import re
import subprocess
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .backup import DatabaseBackup
from .db import DatabaseManager
from .labels import LabelManager
from .tasks import TaskManager
from .utils import filter_tasks_by_date_range, format_task_for_display, get_editor


class EditorManager:
    """Manages task editing in external editor."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize editor manager.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.task_manager = TaskManager(db_manager)
        self.label_manager = LabelManager(db_manager)
        self._editor_opened = False  # Safety flag to track if editor was opened
        self.backup_manager = DatabaseBackup(db_manager.db_path)

    def _generate_task_id(self, task_id: int) -> str:
        """
        Generate a unique reference ID for a task.

        Args:
            task_id: Database task ID

        Returns:
            Unique reference string
        """
        return f"task_{task_id}"

    def _extract_task_id_from_reference(self, reference: str) -> Optional[int]:
        """
        Extract task ID from reference string.

        Args:
            reference: Reference string like "task_123"

        Returns:
            Task ID if valid, None otherwise
        """
        if reference.startswith("task_"):
            try:
                return int(reference[5:])  # Remove "task_" prefix
            except ValueError:
                return None
        return None

    def parse_task_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a task line to extract task info.

        Args:
            line: Task line from the file

        Returns:
            Dictionary with task info or None if not a valid task line
        """
        # Match task line pattern: [ ] or [x] followed by timestamp, content, and optional reference
        # Format: [ ] 2024-01-01 10:00  Task content  #labels  #ref:task_123
        # First, try to match with reference
        pattern_with_ref = r"^(\[ \]|\[x\]) (\d{4}-\d{2}-\d{2} \d{2}:\d{2})  (.+?)(  #.+)?  #ref:([^ ]+)$"
        match = re.match(pattern_with_ref, line.strip())

        if match:
            # Line has a reference
            status = match.group(1)
            timestamp = match.group(2)
            content = match.group(3)
            labels_part = match.group(4) or ""
            reference_part = match.group(5) or ""
        else:
            # Try to match without reference (for new tasks)
            pattern_without_ref = (
                r"^(\[ \]|\[x\]) (\d{4}-\d{2}-\d{2} \d{2}:\d{2})  (.+?)(  #.+)?$"
            )
            match = re.match(pattern_without_ref, line.strip())

            if match:
                # Line has timestamp but no reference
                status = match.group(1)
                timestamp = match.group(2)
                content = match.group(3)
                labels_part = match.group(4) or ""
                reference_part = ""
            else:
                # Try to match new tasks without timestamp (just checkbox and content)
                pattern_new_task = r"^(\[ \]|\[\]|\[x\]) (.+?)(  #.+)?$"
                match = re.match(pattern_new_task, line.strip())

                if not match:
                    return None

                status = match.group(1)
                timestamp = ""  # No timestamp for new tasks
                content = match.group(2)
                labels_part = match.group(3) or ""
                reference_part = ""

        # Extract labels from hashtags (excluding the reference)
        labels = []
        if labels_part:
            hashtags = re.findall(r"#([^,#]+)", labels_part)
            labels = [tag.strip() for tag in hashtags]

        # Normalize status - handle both [] and [ ] as incomplete
        is_completed = status == "[x]"
        if status == "[]":
            status = "[ ]"  # Normalize to standard format
        task_id = self._extract_task_id_from_reference(reference_part)

        return {
            "status": status,
            "timestamp": timestamp,
            "content": content,
            "labels": labels,
            "is_completed": is_completed,
            "task_id": task_id,  # None for new tasks
        }

    def find_matching_task(self, task_info: Dict[str, Any]) -> Optional[int]:
        """
        Find a matching task in the database based on reference ID.

        Args:
            task_info: Parsed task information

        Returns:
            Task ID if found, None otherwise
        """
        # If we have a task_id from the reference, use it directly
        if task_info.get("task_id") is not None:
            # Verify the task still exists
            try:
                task = self.task_manager.get_task(task_info["task_id"])
                if task:
                    return task_info["task_id"]
            except:
                pass
        return None

    def get_tasks_for_editing(
        self,
        label: Optional[str] = None,
        target_date: Optional[str] = None,
        all_tasks: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get tasks for editing based on criteria.
        This method does NOT open the editor - it only retrieves tasks.

        Args:
            label: Optional label to filter by
            target_date: Optional date to filter by (YYYY-MM-DD format)
            all_tasks: If True, return all tasks regardless of date

        Returns:
            List of tasks to edit
        """
        if all_tasks:
            # Return all tasks when --all flag is used
            return self.task_manager.list_tasks(include_completed=True)
        elif label:
            # Filter by label - handle both string and tuple
            label_str = label[0] if isinstance(label, (tuple, list)) else label
            return self.label_manager.filter_tasks_by_label(
                label_str, include_completed=True
            )
        # Apply date filtering if no specific date is provided
        if not target_date:
            all_tasks = self.task_manager.list_tasks(include_completed=all_tasks)
            return filter_tasks_by_date_range(all_tasks, days=1)
        else:
            # Filter by date
            all_tasks = self.task_manager.list_tasks(include_completed=True)
            filtered_tasks = []

            for task in all_tasks:
                task_date = None

                if task["completed_at"]:
                    completed_dt = datetime.fromisoformat(
                        task["completed_at"].replace("Z", "+00:00")
                    )
                    task_date = completed_dt.date()
                else:
                    created_dt = datetime.fromisoformat(
                        task["created_at"].replace("Z", "+00:00")
                    )
                    task_date = created_dt.date()

                try:
                    target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
                    if task_date == target_dt:
                        filtered_tasks.append(task)
                except ValueError:
                    # Invalid date format, skip this filter
                    pass

            return filtered_tasks

    def create_edit_file_content(self, tasks: List[Dict[str, Any]]) -> str:
        """
        Create the content for the edit file without opening the editor.
        This is safe to call and doesn't trigger any external processes.

        Args:
            tasks: List of tasks to include in the file

        Returns:
            String content for the edit file
        """
        if not tasks:
            return ""

        content_lines = [
            "# Fin Tasks - Edit and save to update completion status",
            "# Changes tracked:",
            "#   • Checkbox changes ([ ] ↔ [x]) - mark complete/incomplete",
            "#   • Content changes - reword tasks (keeps same task ID)",
            "#   • New tasks - add lines without #ref:task_XXX",
            "#   • Task deletion - remove lines to delete tasks",
            "# Lines starting with # are ignored",
            "# DO NOT modify the #ref:task_XXX part - it's used to track changes",
            "",
        ]

        for task in tasks:
            task_line = self._format_task_with_reference(task)
            content_lines.append(task_line)

        return "\n".join(content_lines)

    def _format_task_with_reference(self, task: Dict[str, Any]) -> str:
        """
        Format a task for display with its reference ID.

        Args:
            task: Task dictionary

        Returns:
            Formatted task line with reference
        """
        # Get the base formatted line
        base_line = format_task_for_display(task)

        # Add the reference ID
        task_id = task["id"]
        reference = self._generate_task_id(task_id)

        return f"{base_line}  #ref:{reference}"

    def parse_edited_content(
        self, content: str, original_task_ids: Optional[Set[int]] = None
    ) -> tuple:
        """
        Parse edited content and return completion statistics.
        This method is safe and doesn't open any external processes.

        Args:
            content: The edited file content as a string
            original_task_ids: Set of task IDs that were in the original file (for deletion tracking)

        Returns:
            Tuple of (completed_count, reopened_count, new_tasks_count)
        """
        completed_count = 0
        reopened_count = 0
        new_tasks_count = 0
        processed_task_ids = set()

        for line in content.splitlines():
            # Skip header lines and empty lines
            if line.startswith("#") or line.strip() == "":
                continue

            # Parse the task line
            task_info = self.parse_task_line(line)
            if not task_info:
                continue

            # Handle new tasks (those without a reference ID)
            if task_info["task_id"] is None:
                # This is a new task
                if task_info["content"].strip():  # Only add if content is not empty
                    # Add current timestamp for new tasks that don't have one
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

                    # Add the task to the database
                    task_id = self.task_manager.add_task(
                        task_info["content"],
                        labels=task_info["labels"] if task_info["labels"] else None,
                    )
                    new_tasks_count += 1

                    # Update the task with the current timestamp if it didn't have one
                    if not task_info.get("timestamp"):
                        with self.db_manager.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE tasks SET created_at = ? WHERE id = ?",
                                (current_time, task_id),
                            )
                            conn.commit()
                continue

            # Handle existing tasks
            task_id = self.find_matching_task(task_info)
            if not task_id:
                continue

            # Track that we've processed this task
            processed_task_ids.add(task_id)

            # Update completion status if changed
            if self.task_manager.update_task_completion(
                task_id, task_info["is_completed"]
            ):
                if task_info["is_completed"]:
                    completed_count += 1
                else:
                    reopened_count += 1

        # Handle task deletions if we have the original task IDs
        deleted_count = 0
        if original_task_ids:
            deleted_task_ids = original_task_ids - processed_task_ids
            for task_id in deleted_task_ids:
                try:
                    if self.task_manager.delete_task(task_id):
                        deleted_count += 1
                except:
                    # Task might already be deleted or not exist
                    pass

        return completed_count, reopened_count, new_tasks_count, deleted_count

    def edit_tasks(
        self,
        label: Optional[str] = None,
        target_date: Optional[str] = None,
        all_tasks: bool = False,
    ) -> tuple:
        """
        Edit tasks in external editor.
        This is the ONLY method that opens an external editor.
        It should only be called when the user explicitly requests it.

        Args:
            label: Optional label to filter by
            target_date: Optional date to filter by

        Returns:
            Tuple of (completed_count, reopened_count, new_tasks_count, deleted_count)
        """
        # Safety check - prevent accidental editor opening
        if self._editor_opened:
            raise RuntimeError("Editor has already been opened in this session")

        # Get tasks for editing
        tasks = self.get_tasks_for_editing(label, target_date, all_tasks)

        if not tasks:
            return 0, 0, 0, 0

        # Create backup before editing
        backup_id = self.backup_manager.create_backup(
            "Auto-backup before editor session"
        )

        # Track original task IDs for deletion detection
        original_task_ids = {task["id"] for task in tasks}

        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as temp_file:
            # Write header and tasks
            file_content = self.create_edit_file_content(tasks)
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        try:
            # Get editor command
            editor_cmd = get_editor()

            # Split editor command if it contains spaces
            editor_parts = editor_cmd.split()

            # Mark that we're about to open the editor
            self._editor_opened = True

            # Open the editor - this is the only blocking operation
            result = subprocess.run(editor_parts + [temp_file_path])

            if result.returncode != 0:
                # Editor was closed with error, clean up and return
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass
                return 0, 0, 0, 0

            # Read the edited file
            with open(temp_file_path, "r") as f:
                edited_content = f.read()

            # Parse changes and update database
            completed_count, reopened_count, new_tasks_count, deleted_count = (
                self.parse_edited_content(edited_content, original_task_ids)
            )

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass  # File might already be deleted

        return completed_count, reopened_count, new_tasks_count, deleted_count

    def simulate_edit_with_content(
        self, original_content: str, modified_content: str
    ) -> tuple:
        """
        Simulate editing tasks with provided content for testing purposes.
        This method does NOT open any external editor.

        Args:
            original_content: Original file content
            modified_content: Modified file content

        Returns:
            Tuple of (completed_count, reopened_count, new_tasks_count)
        """
        # Extract original task IDs from the original content for deletion tracking
        original_task_ids = set()
        for line in original_content.splitlines():
            if line.startswith("#") or line.strip() == "":
                continue
            task_info = self.parse_task_line(line)
            if task_info and task_info["task_id"] is not None:
                task_id = self.find_matching_task(task_info)
                if task_id:
                    original_task_ids.add(task_id)

        # Parse the modified content to get completion statistics
        return self.parse_edited_content(modified_content, original_task_ids)
