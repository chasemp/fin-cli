"""
Utils module for FinCLI

Contains date/time helpers, formatting, and utility functions.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional


def is_important_task(task: Dict[str, Any]) -> bool:
    """
    Check if a task is marked as important (has #i label).

    Args:
        task: Task dictionary

    Returns:
        True if task has important label, False otherwise
    """
    if not task.get("labels"):
        return False

    return "i" in task["labels"]


def is_today_task(task: Dict[str, Any]) -> bool:
    """
    Check if a task is marked as today (has #t label).

    Args:
        task: Task dictionary

    Returns:
        True if task has today label, False otherwise
    """
    if not task.get("labels"):
        return False

    return "t" in task["labels"]


def format_date_by_format(date_obj: datetime, format_str: str) -> str:
    """
    Format a date according to a custom format string.

    Supported format tokens:
    - M: Month without leading zero (1-12)
    - MM: Month with leading zero (01-12)
    - D: Day without leading zero (1-31)
    - DD: Day with leading zero (01-31)
    - YYYY: Full year (2025)
    - YY: Short year (25)
    - H: Hour without leading zero (0-23)
    - HH: Hour with leading zero (00-23)
    - m: Minute without leading zero (0-59)
    - mm: Minute with leading zero (00-59)

    Args:
        date_obj: datetime object to format
        format_str: Format string (e.g., "M/D", "MM/DD", "M-D")

    Returns:
        Formatted date string
    """
    if not date_obj or not format_str:
        return date_obj.strftime("%Y-%m-%d %H:%M") if date_obj else ""

    result = format_str

    # Replace format tokens with actual values (longer tokens first to avoid conflicts)
    replacements = [
        ("YYYY", str(date_obj.year)),
        ("YY", str(date_obj.year)[-2:]),
        ("MM", f"{date_obj.month:02d}"),
        ("DD", f"{date_obj.day:02d}"),
        ("HH", f"{date_obj.hour:02d}"),
        ("mm", f"{date_obj.minute:02d}"),
        ("M", str(date_obj.month)),
        ("D", str(date_obj.day)),
        ("H", str(date_obj.hour)),
        ("m", str(date_obj.minute)),
    ]

    for token, value in replacements:
        result = result.replace(token, value)

    return result


def wrap_text(text: str, max_width: int, prefix: str = "") -> str:
    """
    Wrap text to fit within a specified width, respecting word boundaries.

    Args:
        text: Text to wrap
        max_width: Maximum width for each line
        prefix: Prefix to add to continuation lines (e.g., indentation)

    Returns:
        Wrapped text with newlines
    """
    if not text or max_width <= 0:
        return text

    # Calculate available width for content (accounting for prefix)
    available_width = max_width - len(prefix)
    if available_width <= 0:
        return text

    words = text.split()
    if not words:
        return text

    lines = []
    current_line = []
    current_length = 0

    for word in words:
        # Check if adding this word would exceed the line width
        word_length = len(word)
        if current_line and current_length + 1 + word_length > available_width:
            # Line is full, start a new one
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = word_length
        else:
            # Add word to current line
            if current_line:
                current_length += 1 + word_length  # +1 for space
            else:
                current_length = word_length
            current_line.append(word)

    # Add the last line
    if current_line:
        lines.append(" ".join(current_line))

    # Join lines with newlines and add prefix to continuation lines
    if len(lines) == 1:
        return lines[0]
    else:
        result = [lines[0]]
        for line in lines[1:]:
            result.append(f"{prefix}{line}")
        return "\n".join(result)


def format_task_for_display(task: Dict[str, Any], config=None) -> str:
    """
    Format a task for display in syslog-like Markdown format.

    Args:
        task: Task dictionary from database
        config: Optional Config instance for wrapping settings

    Returns:
        Formatted string: 1 [ ] 2025-07-30 09:15  Task content  #label1,label2
        For modified tasks: 1 [x] 2025-07-30 09:15 (mod: 2025-07-31 14:30)  Task content  #label1,label2
    """
    # Get task ID
    task_id = task["id"]

    # Determine status
    status = "[x]" if task["completed_at"] else "[ ]"

    # Format primary timestamp
    if task["completed_at"]:
        # Use completed_at for completed tasks
        primary_timestamp = datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00"))
        if config and hasattr(config, "get_task_date_format"):
            primary_time_str = format_date_by_format(primary_timestamp, config.get_task_date_format())
        else:
            primary_time_str = primary_timestamp.strftime("%Y-%m-%d %H:%M")
    else:
        # Use created_at for open tasks
        primary_timestamp = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00"))
        if config and hasattr(config, "get_task_date_format"):
            primary_time_str = format_date_by_format(primary_timestamp, config.get_task_date_format())
        else:
            primary_time_str = primary_timestamp.strftime("%Y-%m-%d %H:%M")

    # Check if task was modified after creation/completion
    modification_indicator = ""

    if task.get("modified_at"):
        modified_timestamp = datetime.fromisoformat(task["modified_at"].replace("Z", "+00:00"))

        if task["completed_at"]:
            # For completed tasks, check if modified after completion
            completed_timestamp = datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00"))
            if modified_timestamp > completed_timestamp:
                if config and hasattr(config, "get_task_date_format"):
                    mod_time_str = format_date_by_format(modified_timestamp, config.get_task_date_format())
                else:
                    mod_time_str = modified_timestamp.strftime("%Y-%m-%d %H:%M")
                modification_indicator = f" (mod: {mod_time_str})"
        else:
            # For open tasks, check if modified after creation
            if modified_timestamp > primary_timestamp:
                if config and hasattr(config, "get_task_date_format"):
                    mod_time_str = format_date_by_format(modified_timestamp, config.get_task_date_format())
                else:
                    mod_time_str = modified_timestamp.strftime("%Y-%m-%d %H:%M")
                modification_indicator = f" (mod: {mod_time_str})"

    # Format labels as hashtags
    labels_display = ""
    if task["labels"]:
        hashtags = [f"#{label}" for label in task["labels"]]
        labels_display = f"  {','.join(hashtags)}"

    # Format due date (appears at end of line as requested)
    due_date_display = ""
    if task.get("due_date"):
        due_date_display = f"  due:{task['due_date']}"

    # Build the base line without content
    base_line = f"{task_id} {status} {primary_time_str}{modification_indicator}  "

    # Get the content and apply wrapping if config is provided
    content = task["content"]
    if config and hasattr(config, "get_task_title_wrap_width"):
        wrap_width = config.get_task_title_wrap_width()
        if wrap_width > 0:
            content = wrap_text(content, wrap_width, base_line)

    return f"{base_line}{content}{labels_display}{due_date_display}"


def get_date_range(days: int = 1, weekdays_only: bool = True) -> tuple:
    """
    Get date ranges for task filtering.

    Args:
        days: Number of days to look back (default: 1 for today and yesterday)
        weekdays_only: If True, count only weekdays (Monday-Friday)

    Returns:
        Tuple of (today, lookback_date) dates
        If days=0, returns (today, None) to indicate no date restriction
    """
    today = date.today()

    # Special case: days=0 means all time (no date restriction)
    if days == 0:
        return today, None

    if weekdays_only:
        # Count only weekdays (Monday=0, Sunday=6)
        lookback_date = today
        weekdays_counted = 0

        # Count backwards until we've counted the required number of weekdays
        while weekdays_counted < days:
            lookback_date = lookback_date - timedelta(days=1)
            # Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4
            if lookback_date.weekday() < 5:  # 0-4 are Monday through Friday
                weekdays_counted += 1
    else:
        # Count all days (original behavior)
        lookback_date = today - timedelta(days=days)

    return today, lookback_date


def filter_tasks_by_date_range(tasks: List[Dict[str, Any]], days: int = 1, weekdays_only: bool = True) -> List[Dict[str, Any]]:
    """
    Filter tasks based on time and status criteria.

    Args:
        tasks: List of task dictionaries
        days: Number of days to look back (default: 1 for today and yesterday)
        weekdays_only: If True, count only weekdays (Monday-Friday)

    Returns:
        List of filtered tasks
    """
    today, lookback_date = get_date_range(days, weekdays_only)

    # If lookback_date is None, it means no date restriction (all time)
    if lookback_date is None:
        # Return all tasks without date filtering
        filtered_tasks = tasks
    else:
        # Filter tasks based on criteria
        filtered_tasks = []

        for task in tasks:
            task_date = None

            # Determine the relevant date for filtering
            if task["completed_at"]:
                # For completed tasks, use completion date
                completed_dt = datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00"))
                task_date = completed_dt.date()
            else:
                # For open tasks, use creation date
                created_dt = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00"))
                task_date = created_dt.date()

            # Include tasks from the lookback period
            if lookback_date <= task_date <= today:
                filtered_tasks.append(task)

    # Sort by priority first, then by created_at descending (most recent first)
    # Important tasks (#i) come first, then today tasks (#t), then regular tasks by recency
    filtered_tasks.sort(
        key=lambda x: (
            not is_important_task(x),  # Important tasks first
            not is_today_task(x),  # Then today tasks
            -datetime.fromisoformat(x["created_at"].replace("Z", "+00:00")).timestamp(),  # Then by creation date descending
        )
    )

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


class DateParser:
    """Utility class for parsing and validating due dates in various formats."""

    @staticmethod
    def parse_due_date(date_str: str) -> Optional[str]:
        """
        Parse a due date string into YYYY-MM-DD format.

        Args:
            date_str: Date string in various formats (MM/DD, YYYY-MM-DD, MM/DD/YYYY)

        Returns:
            Date string in YYYY-MM-DD format, or None if invalid
        """
        if not date_str or not date_str.strip():
            return None

        date_str = date_str.strip()
        current_year = date.today().year

        # Try YYYY-MM-DD format first (most explicit)
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            pass

        # Try MM/DD format (assume current year)
        try:
            parsed_date = datetime.strptime(f"{current_year}-{date_str}", "%Y-%m/%d")
            # Check if this date has already passed this year, if so use next year
            if parsed_date.date() < date.today():
                parsed_date = datetime.strptime(f"{current_year + 1}-{date_str}", "%Y-%m/%d")
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            pass

        # Try MM/DD/YYYY format
        try:
            parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            pass

        # Try MM-DD format (assume current year)
        try:
            parsed_date = datetime.strptime(f"{current_year}-{date_str}", "%Y-%m-%d")
            # Check if this date has already passed this year, if so use next year
            if parsed_date.date() < date.today():
                parsed_date = datetime.strptime(f"{current_year + 1}-{date_str}", "%Y-%m-%d")
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            pass

        return None

    @staticmethod
    def validate_due_date(date_str: str) -> bool:
        """
        Validate if a date string is a valid due date.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            True if valid, False otherwise
        """
        try:
            _ = datetime.strptime(date_str, "%Y-%m-%d")
            # Optionally prevent past dates
            # if parsed_date.date() < date.today():
            #     return False
            return True
        except ValueError:
            return False

    @staticmethod
    def is_overdue(due_date_str: str) -> bool:
        """
        Check if a due date is overdue.

        Args:
            due_date_str: Due date in YYYY-MM-DD format

        Returns:
            True if overdue, False otherwise
        """
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            return due_date < date.today()
        except ValueError:
            return False

    @staticmethod
    def is_due_soon(due_date_str: str, days: int = 3) -> bool:
        """
        Check if a due date is coming up soon.

        Args:
            due_date_str: Due date in YYYY-MM-DD format
            days: Number of days to consider "soon" (default: 3)

        Returns:
            True if due soon, False otherwise
        """
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            today = date.today()
            days_until_due = (due_date - today).days
            return 0 <= days_until_due <= days
        except ValueError:
            return False
