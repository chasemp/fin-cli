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


def get_date_range(include_week: bool = False) -> tuple:
    """
    Get date ranges for task filtering.

    Args:
        include_week: If True, include completed tasks from past 7 days

    Returns:
        Tuple of (today, yesterday, week_ago) dates
    """
    today = date.today()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)

    return today, yesterday, week_ago


def filter_tasks_by_date_range(
    tasks: List[Dict[str, Any]], include_week: bool = False
) -> List[Dict[str, Any]]:
    """
    Filter tasks based on time and status criteria.

    Args:
        tasks: List of task dictionaries
        include_week: If True, include completed tasks from past 7 days

    Returns:
        List of filtered tasks
    """
    today, yesterday, week_ago = get_date_range(include_week)

    # Filter tasks based on criteria
    filtered_tasks = []

    for task in tasks:
        task_date = None

        # Determine the relevant date for this task
        if task["completed_at"]:
            # For completed tasks, use completed_at date
            completed_dt = datetime.fromisoformat(
                task["completed_at"].replace("Z", "+00:00")
            )
            task_date = completed_dt.date()
        else:
            # For open tasks, use created_at date
            created_dt = datetime.fromisoformat(
                task["created_at"].replace("Z", "+00:00")
            )
            task_date = created_dt.date()

        # Apply filtering criteria
        if task["completed_at"] is None:
            # Open tasks: show only today's
            if task_date == today:
                filtered_tasks.append(task)
        else:
            # Completed tasks: show yesterday's, or past week if --week flag
            if include_week:
                if week_ago <= task_date <= today:
                    filtered_tasks.append(task)
            else:
                if task_date == yesterday:
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
