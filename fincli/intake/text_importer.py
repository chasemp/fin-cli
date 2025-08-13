"""
Text file importer for FinCLI

Imports tasks from plain text files with optional label support.
"""

import os
from typing import Any, Dict, Optional

from ..db import DatabaseManager
from ..tasks import TaskManager


def import_text_tasks(file_path: str = None, db_manager: Optional[DatabaseManager] = None, **kwargs) -> Dict[str, Any]:
    """
    Import tasks from a text file.

    Expected format:
    Review PR
    Buy groceries

    Or with labels (comma-separated):
    Finish sync script,planning
    Review PR,backend,urgent
    Buy groceries,personal

    Args:
        file_path: Path to text file (defaults to ~/.fin/tasks.txt)
        db_manager: Database manager instance (optional, will create one if not provided)
        **kwargs: Additional arguments

    Returns:
        Dictionary with import results
    """
    if file_path is None:
        file_path = os.path.expanduser("~/fin/tasks.txt")

    if not os.path.exists(file_path):
        return {
            "success": False,
            "error": f"Text file not found: {file_path}",
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
        with open(file_path, "r", encoding="utf-8") as textfile:
            for line_num, line in enumerate(textfile, start=1):
                try:
                    line = line.strip()

                    if not line or line.startswith("#"):
                        continue  # Skip empty lines and comments

                    # Check if line contains labels (comma-separated)
                    if "," in line:
                        # Split on first comma to separate task from labels
                        parts = line.split(",", 1)
                        task_content = parts[0].strip()
                        labels_str = parts[1].strip()

                        # Parse labels
                        labels = [
                            label.strip()
                            for label in labels_str.split(",")
                            if label.strip()
                        ]
                    else:
                        # No labels, just task content
                        task_content = line
                        labels = []

                    if not task_content:
                        skipped_count += 1
                        continue

                    # Add source label
                    labels.append("source:text")

                    # Add task to database
                    task_manager.add_task(task_content, labels, source="text-import")
                    imported_count += 1

                except Exception as e:
                    errors.append(f"Line {line_num}: {str(e)}")
                    skipped_count += 1

        # Optionally remove the text file after successful import
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
            "error": f"Failed to read text file: {str(e)}",
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": errors,
        }
