"""
Editor module for FinCLI

Handles the fine command functionality for editing tasks in an external editor.
"""

import os
import re
import subprocess
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

from .db import DatabaseManager
from .labels import LabelManager
from .tasks import TaskManager
from .utils import (filter_tasks_by_date_range, format_task_for_display,
                    get_editor)


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

    def parse_task_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a task line to extract task info.

        Args:
            line: Task line from the file

        Returns:
            Dictionary with task info or None if not a valid task line
        """
        # Match task line pattern: [ ] or [x] followed by timestamp and content
        pattern = r"^(\[ \]|\[x\]) (\d{4}-\d{2}-\d{2} \d{2}:\d{2})  (.+?)(  #.+)?$"
        match = re.match(pattern, line.strip())

        if not match:
            return None

        status = match.group(1)
        timestamp = match.group(2)
        content = match.group(3)
        labels_part = match.group(4) or ""

        # Extract labels from hashtags
        labels = []
        if labels_part:
            hashtags = re.findall(r"#([^,#]+)", labels_part)
            labels = [tag.strip() for tag in hashtags]

        is_completed = status == "[x]"

        return {
            "status": status,
            "timestamp": timestamp,
            "content": content,
            "labels": labels,
            "is_completed": is_completed,
        }

    def find_matching_task(self, task_info: Dict[str, Any]) -> Optional[int]:
        """
        Find a matching task in the database based on content, timestamp, and labels.

        Args:
            task_info: Parsed task information

        Returns:
            Task ID if found, None otherwise
        """
        all_tasks = self.task_manager.list_tasks(include_completed=True)

        for task in all_tasks:
            # Check if content matches
            if task["content"] != task_info["content"]:
                continue

            # Check if labels match
            task_labels = set(task["labels"]) if task["labels"] else set()
            info_labels = set(task_info["labels"])
            if task_labels != info_labels:
                continue

            # Check if timestamp matches (allowing for slight differences)
            task_timestamp = None
            if task["completed_at"]:
                task_timestamp = datetime.fromisoformat(
                    task["completed_at"].replace("Z", "+00:00")
                ).strftime("%Y-%m-%d %H:%M")
            else:
                task_timestamp = datetime.fromisoformat(
                    task["created_at"].replace("Z", "+00:00")
                ).strftime("%Y-%m-%d %H:%M")

            if task_timestamp == task_info["timestamp"]:
                return task["id"]

        return None

    def get_tasks_for_editing(
        self, label: Optional[str] = None, target_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tasks for editing based on criteria.

        Args:
            label: Optional label to filter by
            target_date: Optional date to filter by (YYYY-MM-DD format)

        Returns:
            List of tasks to edit
        """
        if label:
            # Filter by label - handle both string and tuple
            label_str = label[0] if isinstance(label, (tuple, list)) else label
            return self.label_manager.filter_tasks_by_label(
                label_str, include_completed=True
            )
        elif target_date:
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
        else:
            # Use default filtering (today's open + yesterday's completed)
            all_tasks = self.task_manager.list_tasks(include_completed=True)
            return filter_tasks_by_date_range(all_tasks, include_week=False)

    def edit_tasks(
        self, label: Optional[str] = None, target_date: Optional[str] = None
    ) -> tuple:
        """
        Edit tasks in external editor.

        Args:
            label: Optional label to filter by
            target_date: Optional date to filter by

        Returns:
            Tuple of (completed_count, reopened_count)
        """
        # Get tasks for editing
        tasks = self.get_tasks_for_editing(label, target_date)

        if not tasks:
            return 0, 0

        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as temp_file:
            # Write header
            temp_file.write("# Fin Tasks - Edit and save to update completion status\n")
            temp_file.write("# Only checkbox changes ([ ] ↔ [x]) are tracked\n\n")

            # Write tasks
            for task in tasks:
                task_line = format_task_for_display(task)
                temp_file.write(task_line + "\n")

            temp_file_path = temp_file.name

        # Get editor command
        editor_cmd = get_editor()

        # Split editor command if it contains spaces
        editor_parts = editor_cmd.split()
        result = subprocess.run(editor_parts + [temp_file_path])

        if result.returncode != 0:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
            return 0, 0

        # Read the edited file
        with open(temp_file_path, "r") as f:
            edited_lines = f.readlines()

        # Parse changes and update database
        completed_count = 0
        reopened_count = 0

        for line in edited_lines:
            # Skip header lines and empty lines
            if line.startswith("#") or line.strip() == "":
                continue

            # Parse the task line
            task_info = self.parse_task_line(line)
            if not task_info:
                continue

            # Find matching task in database
            task_id = self.find_matching_task(task_info)
            if not task_id:
                continue

            # Update completion status if changed
            if self.task_manager.update_task_completion(
                task_id, task_info["is_completed"]
            ):
                if task_info["is_completed"]:
                    completed_count += 1
                else:
                    reopened_count += 1

        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except OSError:
            pass  # File might already be deleted

        return completed_count, reopened_count
