"""
Utils module for FinCLI

Contains date/time helpers, formatting, and utility functions.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List


def format_task_for_display(task: Dict[str, Any]) -> str:
    """
    Format a task for display in syslog-like Markdown format.

    Args:
        task: Task dictionary from database

    Returns:
        Formatted string: [ ] 2025-07-30 09:15  Task content  #label1,label2
    """
    # Determine status
    status = "[x]" if task["completed_at"] else "[ ]"

    # Format timestamp
    if task["completed_at"]:
        # Use completed_at for completed tasks
        timestamp = datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00"))
    else:
        # Use created_at for open tasks
        timestamp = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00"))

    formatted_time = timestamp.strftime("%Y-%m-%d %H:%M")

    # Format labels as hashtags
    labels_display = ""
    if task["labels"]:
        hashtags = [f"#{label}" for label in task["labels"]]
        labels_display = f"  {','.join(hashtags)}"

    return f"{status} {formatted_time}  {task['content']}{labels_display}"


def get_date_range(days: int = 1) -> tuple:
    """
    Get date ranges for task filtering.

    Args:
        days: Number of days to look back (default: 1 for today and yesterday)

    Returns:
        Tuple of (today, lookback_date) dates
    """
    today = date.today()
    lookback_date = today - timedelta(days=days)

    return today, lookback_date


def filter_tasks_by_date_range(
    tasks: List[Dict[str, Any]], days: int = 1
) -> List[Dict[str, Any]]:
    """
    Filter tasks based on time and status criteria.

    Args:
        tasks: List of task dictionaries
        days: Number of days to look back for completed tasks (default: 1)

    Returns:
        List of filtered tasks
    """
    today, lookback_date = get_date_range(days)

    # Filter tasks based on criteria
    filtered_tasks = []

    for task in tasks:
        # Always include open tasks regardless of creation date
        if task["completed_at"] is None:
            filtered_tasks.append(task)
        else:
            # For completed tasks, apply date filtering
            completed_dt = datetime.fromisoformat(
                task["completed_at"].replace("Z", "+00:00")
            )
            task_date = completed_dt.date()

            # Include completed tasks from the lookback period
            if lookback_date <= task_date <= today:
                filtered_tasks.append(task)

    # Sort by created_at ascending
    filtered_tasks.sort(key=lambda x: x["created_at"])

    return filtered_tasks


def get_editor() -> str:
    """
    Get the editor command to use.

    Returns:
        Editor command string
    """
    import os
    import subprocess

    editor = os.environ.get("EDITOR")
    if editor:
        return editor

    # Fallback editors
    for fallback in ["nano", "vim", "code"]:
        if subprocess.run(["which", fallback], capture_output=True).returncode == 0:
            return fallback

    # Final fallback
    return "nano"
