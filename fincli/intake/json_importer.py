"""
JSON importer for FinCLI

Imports tasks from JSON files with label support.
"""

import json
import os
from typing import Any, Dict, Optional

from ..db import DatabaseManager
from ..tasks import TaskManager


def import_json_tasks(
    file_path: str = None, db_manager: Optional[DatabaseManager] = None, **kwargs
) -> Dict[str, Any]:
    """
    Import tasks from a JSON file.

    Expected JSON format:
    [
        {"task": "Finish sync script", "labels": ["planning", "work"]},
        {"task": "Review PR", "labels": ["backend", "urgent"]}
    ]

    Args:
        file_path: Path to JSON file (defaults to ~/.fin/tasks.json)
        db_manager: Database manager instance (optional, will create one if not provided)
        **kwargs: Additional arguments

    Returns:
        Dictionary with import results
    """
    if file_path is None:
        file_path = os.path.expanduser("~/fin/tasks.json")

    if not os.path.exists(file_path):
        return {
            "success": False,
            "error": f"JSON file not found: {file_path}",
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
        with open(file_path, "r", encoding="utf-8") as jsonfile:
            data = json.load(jsonfile)

        if not isinstance(data, list):
            return {
                "success": False,
                "error": "JSON file must contain an array of tasks",
                "imported": 0,
                "skipped": 0,
            }

        for item_num, item in enumerate(data, start=1):
            try:
                if not isinstance(item, dict):
                    errors.append(f"Item {item_num}: Not a valid task object")
                    skipped_count += 1
                    continue

                # Extract task content and labels
                task_content = item.get("task", "").strip()
                labels = item.get("labels", [])

                if not task_content:
                    skipped_count += 1
                    continue

                # Ensure labels is a list
                if isinstance(labels, str):
                    labels = [labels]
                elif not isinstance(labels, list):
                    labels = []

                # Add source label
                labels.append("source:json")

                # Add task to database
                task_manager.add_task(task_content, labels, source="json-import")
                imported_count += 1

            except Exception as e:
                errors.append(f"Item {item_num}: {str(e)}")
                skipped_count += 1

        # Optionally remove the JSON file after successful import
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

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Invalid JSON format: {str(e)}",
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": errors,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read JSON file: {str(e)}",
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": errors,
        }
