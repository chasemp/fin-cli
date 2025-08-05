"""
Tasks module for FinCLI

Handles CRUD operations for tasks.
"""

import re
from typing import Any, Dict, List, Optional

from .db import DatabaseManager


class TaskManager:
    """Manages task CRUD operations."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize task manager.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    def add_task(
        self,
        content: str,
        labels: Optional[List[str]] = None,
        source: str = "cli",
    ) -> int:
        """
        Add a new task to the database.

        Args:
            content: The task description (markdown-formatted)
            labels: Optional list of labels (will be normalized and stored as comma-separated)
            source: Source of the task (default: "cli")

        Returns:
            The ID of the newly created task
        """
        # Normalize labels
        labels_str = None
        if labels:
            # Normalize labels: split on comma or space, lowercase, trim whitespace
            all_labels = []
            for label_group in labels:
                if label_group:
                    # Split on comma or space, then normalize each label
                    split_labels = re.split(r"[, ]+", label_group.strip())
                    for label in split_labels:
                        if label.strip():
                            all_labels.append(label.strip().lower())

            # Remove duplicates and sort
            unique_labels = sorted(list(set(all_labels)))
            labels_str = ",".join(unique_labels) if unique_labels else None

        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO tasks (content, labels, source)
                VALUES (?, ?, ?)
            """,
                (content, labels_str, source),
            )

            task_id = cursor.lastrowid
            conn.commit()

            return task_id

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.

        Args:
            task_id: Task ID to retrieve

        Returns:
            Task dictionary or None if not found
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, content, created_at, completed_at, labels, source
                FROM tasks
                WHERE id = ?
            """,
                (task_id,),
            )

            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "content": row[1],
                    "created_at": row[2],
                    "completed_at": row[3],
                    "labels": row[4].split(",") if row[4] else [],
                    "source": row[5],
                }
            return None

    def list_tasks(self, include_completed: bool = True) -> List[Dict[str, Any]]:
        """
        List all tasks, optionally including completed ones.

        Args:
            include_completed: Whether to include completed tasks

        Returns:
            List of task dictionaries
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, content, created_at, completed_at, labels, source
                FROM tasks
            """

            if not include_completed:
                query += " WHERE completed_at IS NULL"

            query += " ORDER BY created_at DESC"

            cursor.execute(query)

            tasks = []
            for row in cursor.fetchall():
                tasks.append(
                    {
                        "id": row[0],
                        "content": row[1],
                        "created_at": row[2],
                        "completed_at": row[3],
                        "labels": row[4].split(",") if row[4] else [],
                        "source": row[5],
                    }
                )

            return tasks

    def update_task_completion(self, task_id: int, is_completed: bool) -> bool:
        """
        Update task completion status.

        Args:
            task_id: Task ID to update
            is_completed: Whether the task should be marked as completed

        Returns:
            True if updated, False if no change needed
        """
        task = self.get_task(task_id)
        if not task:
            return False

        current_completed = task["completed_at"] is not None
        if current_completed == is_completed:
            return False  # No change needed

        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            if is_completed:
                # Mark as completed
                cursor.execute(
                    "UPDATE tasks SET completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (task_id,),
                )
            else:
                # Mark as reopened
                cursor.execute(
                    "UPDATE tasks SET completed_at = NULL WHERE id = ?",
                    (task_id,),
                )

            conn.commit()

        return True

    def delete_task(self, task_id: int) -> bool:
        """
        Delete a task by ID.

        Args:
            task_id: Task ID to delete

        Returns:
            True if deleted, False if not found
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM tasks WHERE id = ?",
                (task_id,),
            )

            conn.commit()

            return cursor.rowcount > 0
