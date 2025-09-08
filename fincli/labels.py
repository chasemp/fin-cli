"""
Labels module for FinCLI

Handles label management and filtering.
"""

from typing import Any, Dict, List

from .db import DatabaseManager


class LabelManager:
    """Manages label operations."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize label manager.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    def get_all_labels(self) -> List[str]:
        """
        Get all unique labels from all tasks.

        Returns:
            List of unique labels, sorted alphabetically
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT labels FROM tasks WHERE labels IS NOT NULL AND labels != ''
            """
            )

            all_labels = []
            for row in cursor.fetchall():
                if row[0]:
                    labels = row[0].split(",")
                    all_labels.extend([label.strip() for label in labels if label.strip()])

            # Remove duplicates and sort
            return sorted(list(set(all_labels)))

    def filter_tasks_by_label(self, label: str, include_completed: bool = True) -> List[Dict[str, Any]]:
        """
        Filter tasks by label (case-insensitive, partial match).

        Args:
            label: Label to filter by (case-insensitive)
            include_completed: Whether to include completed tasks

        Returns:
            List of tasks that match the label
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, content, created_at, completed_at, labels, source
                FROM tasks
                WHERE labels LIKE ?
            """

            if not include_completed:
                query += " AND completed_at IS NULL"

            query += " ORDER BY created_at DESC"

            # Use case-insensitive pattern matching
            pattern = f"%{str(label).lower()}%"
            cursor.execute(query, (pattern,))

            tasks = []
            for row in cursor.fetchall():
                task_labels = row[4].split(",") if row[4] else []
                # Additional check for exact label match (case-insensitive)
                if any(str(label).lower() in task_label.lower() for task_label in task_labels):
                    tasks.append(
                        {
                            "id": row[0],
                            "content": row[1],
                            "created_at": row[2],
                            "completed_at": row[3],
                            "labels": task_labels,
                            "source": row[5],
                        }
                    )

            return tasks

    def get_label_counts(self) -> Dict[str, Dict[str, int]]:
        """
        Get counts of tasks for each label, broken down by status.

        Returns:
            Dictionary mapping label names to counts:
            {"label": {"open": count, "completed": count, "total": count}}
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT labels, completed_at FROM tasks 
                WHERE labels IS NOT NULL AND labels != ''
                """
            )

            label_counts = {}
            for row in cursor.fetchall():
                labels_str, completed_at = row
                if labels_str:
                    labels = [label.strip() for label in labels_str.split(",") if label.strip()]
                    is_completed = completed_at is not None

                    for label in labels:
                        if label not in label_counts:
                            label_counts[label] = {"open": 0, "completed": 0, "total": 0}

                        if is_completed:
                            label_counts[label]["completed"] += 1
                        else:
                            label_counts[label]["open"] += 1
                        label_counts[label]["total"] += 1

            return label_counts
