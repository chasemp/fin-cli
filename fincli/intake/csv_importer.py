"""
CSV importer for FinCLI

Imports tasks from CSV files with label support.
"""

import csv
import os
from typing import Any, Dict, Optional

from ..db import DatabaseManager
from ..tasks import TaskManager


def import_csv_tasks(file_path: str = None, db_manager: Optional[DatabaseManager] = None, **kwargs) -> Dict[str, Any]:
    """
    Import tasks from a CSV file.

    Expected CSV format:
    Task,Label
    "Finish sync script",planning
    "Review PR",backend

    Args:
        file_path: Path to CSV file (defaults to ~/.fin/tasks.csv)
        db_manager: Database manager instance (optional, will create one if not provided)
        **kwargs: Additional arguments

    Returns:
        Dictionary with import results
    """
    if file_path is None:
        file_path = os.path.expanduser("~/fin/tasks.csv")

    if not os.path.exists(file_path):
        return {
            "success": False,
            "error": f"CSV file not found: {file_path}",
            "imported": 0,
            "skipped": 0,
        }

    # Initialize managers - use provided db_manager or create one
    if db_manager is None:
        db_manager = DatabaseManager()
    task_manager = TaskManager(db_manager)

    imported_count = 0
    skipped_count = 0
    errors = []

    try:
        with open(file_path, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                try:
                    # Extract task content and labels
                    task_content = row.get("Task", "").strip()
                    labels_str = row.get("Label", "").strip()

                    if not task_content:
                        skipped_count += 1
                        continue

                    # Parse labels
                    labels = []
                    if labels_str:
                        labels = [label.strip() for label in labels_str.split(",") if label.strip()]

                    # Add source label
                    labels.append("source:csv")

                    # Add task to database
                    task_manager.add_task(task_content, labels, source="csv-import")
                    imported_count += 1

                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    skipped_count += 1

        # Optionally remove the CSV file after successful import
        if imported_count > 0 and kwargs.get("delete_after_import", False):
            try:
                os.remove(file_path)
            except OSError:
                pass  # File might already be deleted

        return {
            "success": True,
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": errors,
            "file_path": file_path,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read CSV file: {str(e)}",
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": errors,
        }
