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
        due_date: Optional[str] = None,
        context: Optional[str] = None,
    ) -> int:
        """
        Add a new task to the database.

        Args:
            content: The task description (markdown-formatted)
            labels: Optional list of labels (will be normalized and stored as comma-separated)
            source: Source of the task (default: "cli")
            due_date: Optional due date in YYYY-MM-DD format
            context: Optional context for the task (defaults to current context or 'default')

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

        # Set default context if none provided
        if context is None:
            context = "default"

        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO tasks (content, labels, source, due_date, context)
                VALUES (?, ?, ?, ?, ?)
            """,
                (content, labels_str, source, due_date, context),
            )

            task_id = cursor.lastrowid
            conn.commit()

            return task_id

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific task by ID.

        Args:
            task_id: Task ID to retrieve

        Returns:
            Task dictionary or None if not found
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, content, created_at, modified_at, completed_at, labels, source, due_date, context
                FROM tasks WHERE id = ?
                """,
                (task_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row[0],
                "content": row[1],
                "created_at": row[2],
                "modified_at": row[3],
                "completed_at": row[4],
                "labels": row[5].split(",") if row[5] else [],
                "source": row[6],
                "due_date": row[7],
                "context": row[8] or "default",
            }

    def list_tasks(self, include_completed: bool = False, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all tasks, optionally including completed ones.

        Args:
            include_completed: Whether to include completed tasks
            context: Optional context to filter by

        Returns:
            List of task dictionaries
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, content, created_at, modified_at, completed_at, labels, source, due_date, context
                FROM tasks
            """

            where_conditions = []
            if not include_completed:
                where_conditions.append("completed_at IS NULL")

            if context:
                where_conditions.append("context = ?")

            if where_conditions:
                query += " WHERE " + " AND ".join(where_conditions)

            query += " ORDER BY created_at DESC"

            if context:
                cursor.execute(query, (context,))
            else:
                cursor.execute(query)

            tasks = []
            for row in cursor.fetchall():
                tasks.append(
                    {
                        "id": row[0],
                        "content": row[1],
                        "created_at": row[2],
                        "modified_at": row[3],
                        "completed_at": row[4],
                        "labels": row[5].split(",") if row[5] else [],
                        "source": row[6],
                        "due_date": row[7],
                        "context": row[8] or "default",
                    }
                )

            return tasks

    def update_task_content(self, task_id: int, new_content: str) -> bool:
        """
        Update task content and set modified_at timestamp.

        Args:
            task_id: Task ID to update
            new_content: New content for the task

        Returns:
            True if updated, False if not found or no change
        """
        task = self.get_task(task_id)
        if not task:
            return False

        if task["content"] == new_content:
            return False  # No change needed

        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE tasks SET content = ?, modified_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_content, task_id),
            )

            conn.commit()

        return True

    def update_task_completion(self, task_id: int, is_completed: bool) -> bool:
        """
        Update task completion status and set modified_at timestamp.

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
                    "UPDATE tasks SET completed_at = CURRENT_TIMESTAMP, modified_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (task_id,),
                )
            else:
                # Mark as reopened
                cursor.execute(
                    "UPDATE tasks SET completed_at = NULL, modified_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (task_id,),
                )

            conn.commit()

        return True

    def update_task_due_date(self, task_id: int, due_date: Optional[str]) -> bool:
        """
        Update task due date and set modified_at timestamp.

        Args:
            task_id: Task ID to update
            due_date: New due date in YYYY-MM-DD format, or None to remove due date

        Returns:
            True if updated, False if not found or no change
        """
        task = self.get_task(task_id)
        if not task:
            return False

        current_due_date = task.get("due_date")
        if current_due_date == due_date:
            return False  # No change needed

        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE tasks SET due_date = ?, modified_at = CURRENT_TIMESTAMP WHERE id = ?",
                (due_date, task_id),
            )

            conn.commit()

        return True

    def update_task_labels(self, task_id: int, labels: Optional[List[str]]) -> bool:
        """
        Update the labels of a task.

        Args:
            task_id: ID of the task to update
            labels: New list of labels, or None to remove all labels

        Returns:
            True if update was successful, False otherwise
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Convert labels list to comma-separated string
                labels_str = None
                if labels:
                    # Normalize labels: lowercase, trim whitespace, remove duplicates
                    normalized_labels = []
                    for label in labels:
                        if label.strip():
                            normalized_labels.append(label.strip().lower())
                    # Remove duplicates and sort
                    unique_labels = sorted(list(set(normalized_labels)))
                    labels_str = ",".join(unique_labels) if unique_labels else None

                cursor.execute(
                    "UPDATE tasks SET labels = ?, modified_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (labels_str, task_id),
                )
                conn.commit()
                return True
        except Exception:
            return False

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
