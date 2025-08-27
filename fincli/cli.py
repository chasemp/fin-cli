"""
FinCLI - A lightweight task tracking system

A modular, installable Python package for managing local tasks.
"""

from datetime import date, datetime, timedelta
import os
import re
import sys
from typing import List, Optional

import click

from fincli import __version__
from fincli.analytics import AnalyticsManager
from fincli.backup import DatabaseBackup
from fincli.config import Config
from fincli.contexts import ContextManager
from fincli.db import DatabaseManager
from fincli.editor import EditorManager
from fincli.intake import import_from_source
from fincli.labels import LabelManager
from fincli.sheets_connector import create_sheets_reader_from_token
from fincli.sync_engine import SyncEngine
from fincli.sync_strategies import RemoteSystemType, SyncStrategyFactory
from fincli.tasks import TaskManager
from fincli.utils import (
    DateParser,
    evaluate_boolean_label_expression,
    filter_tasks_by_date_range,
    format_task_for_display,
    is_important_task,
    is_today_task,
)


def _get_db_manager():
    """Get database manager - lazy initialization to avoid import-time connections."""
    # Check for environment variable first to ensure proper test isolation
    env_db_path = os.environ.get("FIN_DB_PATH")
    if env_db_path:
        return DatabaseManager(env_db_path)
    else:
        return DatabaseManager()


def add_task(content: str, labels: tuple, source: str = "cli", due_date: str = None):
    """Add a task to the database."""
    # Only create database connection when function is called, not at import time
    # Check for environment variable first to ensure proper test isolation
    env_db_path = os.environ.get("FIN_DB_PATH")
    if env_db_path:
        db_manager = DatabaseManager(env_db_path)
    else:
        db_manager = _get_db_manager()

    task_manager = TaskManager(db_manager)
    # config = Config()  # Temporarily disabled to debug hanging issue

    # Convert labels tuple to list for TaskManager
    labels_list = list(labels) if labels else []

    # Validate labels for reserved words
    reserved_words = {"and", "or", "ref", "due", "recur", "depends", "not"}
    invalid_labels = [label for label in labels_list if label.lower() in reserved_words]
    if invalid_labels:
        click.echo(f"❌ Error: Cannot use reserved words as labels: {', '.join(invalid_labels)}")
        click.echo(f"   Reserved words: {', '.join(sorted(reserved_words))}")
        click.echo("   Use complex filtering instead: fin list -l 'work and urgent'")
        click.echo("   Use special patterns: #due:06/17, #due:2025-08-10, #recur:daily, #depends:task123")
        click.echo("   Use NOT logic: fin list -l 'NOT urgent' or 'work AND NOT urgent'")
        sys.exit(1)

    # Check if this is an important task and auto-add today label if configured
    # Temporarily disabled to debug hanging issue
    # if "i" in labels_list and config.get_auto_today_for_important():
    #     if "t" not in labels_list:
    #         labels_list.append("t")

    # Get current context
    current_context = ContextManager.get_current_context()

    # Add the task with due date, labels, and context (TaskManager handles normalization)
    task_manager.add_task(content, labels_list, source, due_date, current_context)

    # Get normalized labels for display (sorted alphabetically)
    normalized_labels = []
    if labels_list:
        # Simple normalization for display: lowercase and trim, then sort
        for label in labels_list:
            if label:
                normalized_labels.append(label.lower().strip())
        # Sort alphabetically to match test expectations
        normalized_labels.sort()

    # Format output to match test expectations
    due_date_display = ""
    if due_date:
        due_date_display = f" (due: {due_date})"

    if normalized_labels:
        click.echo(f'✅ Task added: "{content}" [{", ".join(normalized_labels)}]{due_date_display}')
    else:
        click.echo(f'✅ Task added: "{content}"{due_date_display}')


def handle_direct_task(args):
    """Handle direct task addition: fin "task content"."""
    if not args:
        click.echo("Missing argument")
        sys.exit(1)

    # Parse arguments for labels
    task_content = []
    labels = []
    source = "cli"  # Default source
    i = 0

    while i < len(args):
        if args[i] == "--label" or args[i] == "-l":
            if i + 1 < len(args):
                labels.append(args[i + 1])
                i += 2
            else:
                click.echo("Error: --label requires a value")
                sys.exit(1)
        elif args[i] == "--source":
            if i + 1 < len(args):
                # source variable is used for add_task call
                source = args[i + 1]
                i += 2
            else:
                click.echo("Error: --source requires a value")
                sys.exit(1)
        elif args[i].startswith("-"):
            # Skip other options for now
            i += 1
        else:
            task_content.append(args[i])
            i += 1

    if not task_content:
        click.echo("Missing task content")
        sys.exit(1)

    content = " ".join(task_content)

    # Extract special features first (due dates, recurring, dependencies)
    due_date = None
    recurring = None
    dependencies = []

    # Extract due date: #due:MM/DD or #due:YYYY-MM-DD or #due:MM/DD/YYYY
    due_match = re.search(r"#due:([^ ]+)", content)
    if due_match:
        due_date_raw = due_match.group(1)
        # Parse the due date using DateParser
        due_date = DateParser.parse_due_date(due_date_raw)
        if due_date:
            # Remove the due date from content
            content = re.sub(r"#due:[^ ]+", "", content)
        else:
            click.echo(f"❌ Error: Invalid due date format: {due_date_raw}")
            click.echo("   Supported formats:")
            click.echo("   - MM/DD")
            click.echo("   - YYYY-MM-DD")
            click.echo("   - MM/DD/YYYY")
            sys.exit(1)

    # Extract recurring: #recur:daily, #recur:weekly, etc.
    recur_match = re.search(r"#recur:(\w+)", content)
    if recur_match:
        recurring = recur_match.group(1)
        content = re.sub(r"#recur:\w+", "", content)

    # Extract dependencies: #depends:task123
    dep_matches = re.findall(r"#depends:(\w+)", content)
    if dep_matches:
        dependencies = dep_matches
        content = re.sub(r"#depends:\w+", "", content)

    # Extract hashtags from content and add them as labels
    # Exclude task reference patterns like #task23, #ref:task23, etc.
    # Also exclude special patterns like #due:, #recur:, #depends:
    hashtags = re.findall(r"#(?!task\d+|ref:task\d+|due:|recur:|depends:)(\w+)", content)

    # Validate hashtags for reserved words
    reserved_words = {"and", "or", "ref", "due", "recur", "depends", "not"}
    invalid_hashtags = [tag for tag in hashtags if tag.lower() in reserved_words]
    if invalid_hashtags:
        click.echo(f"❌ Error: Cannot use reserved words as labels: {', '.join(invalid_hashtags)}")
        click.echo(f"   Reserved words: {', '.join(sorted(reserved_words))}")
        click.echo("   Use complex filtering instead: fin list -l 'work and urgent'")
        click.echo("   Use special patterns: #due:2025-08-10, #recur:daily, #depends:task123")
        click.echo("   Use NOT logic: fin list -l 'NOT urgent' or 'work AND NOT urgent'")
        sys.exit(1)

    for hashtag in hashtags:
        labels.append(hashtag)

    # Remove hashtags from content (but preserve task references)
    # First, temporarily replace task references
    content = re.sub(r"#(task\d+|ref:task\d+)", r"__TASK_REF_\1__", content)
    # Remove other hashtags
    content = re.sub(r"#\w+", "", content)
    # Restore task references
    content = re.sub(r"__TASK_REF_(task\d+|ref:task\d+)__", r"#\1", content)

    # Clean up extra whitespace
    content = re.sub(r"\s+", " ", content).strip()

    if not content:
        click.echo("Error: Task content cannot be empty after removing hashtags")
        sys.exit(1)

    # Add special features as labels for now (we'll enhance the database schema later)
    if recurring:
        labels.append(f"recur:{recurring}")
    for dep in dependencies:
        labels.append(f"depends:{dep}")

    add_task(content, tuple(labels), source, due_date)


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(version=__version__, prog_name="FinCLI")
@click.option("--context", "-c", help="Set context for this session (e.g., work, personal)")
def cli(context):
    """FinCLI - A lightweight task tracking system

    Manage your local task database with simple commands.

    Examples:
        fin "my new task"                    # Add a task directly
        fin add-task "my new task"           # Add a task explicitly
        fin list-tasks                       # List all tasks
        fin -c work list                     # Show tasks in work context
    """
    # Set context if provided
    if context:
        try:
            ContextManager.set_context(context)
            click.echo(f"🔧 Context set to: {context}")
        except ValueError as e:
            click.echo(f"❌ Error: {e}")
            sys.exit(1)
    pass


@cli.command(name="add-task")
@click.argument("content", nargs=-1)
@click.option("--label", "-l", multiple=True, help="Labels for the task")
@click.option("--source", default="cli", help="Source of the task")
def add_task_command(content, label, source):
    """Add a new task."""
    if not content:
        sys.stderr.write("Missing argument\n")
        raise click.Abort()
    task_content = " ".join(content)
    add_task(task_content, label, source)


@cli.command(name="add")
@click.argument("content", nargs=-1)
@click.option("--label", "-l", multiple=True, help="Labels for the task")
@click.option("--source", default="cli", help="Source of the task")
def add_command(content, label, source):
    """Add a new task (alias for add-task)."""
    if not content:
        sys.stderr.write("Missing argument\n")
        raise click.Abort()
    task_content = " ".join(content)
    add_task(task_content, label, source)


@cli.command(name="init")
@click.option("--db-path", help="Custom database path (default: ~/fin/tasks.db)")
def init(db_path: str):
    """
    Initialize the Fin task database.

    Creates the database file and sets up the schema if it doesn't exist.
    This command is optional - the database is automatically created when needed.

    Examples:
        fin init
        fin init --db-path ~/my-tasks.db
    """
    DatabaseManager(db_path=db_path)
    # Database is automatically initialized in __init__
    click.echo("✅ Database initialized successfully!")


def _list_tasks_impl(days, label, status, today=False, due=None, verbose=False):
    """Implementation for listing tasks."""
    db_manager = _get_db_manager()
    task_manager = TaskManager(db_manager)
    config = Config()

    # Get current context first (needed for verbose output and filtering)
    current_context = ContextManager.get_current_context()

    # Show verbose information about filtering criteria
    if verbose:
        click.echo("🔍 Filtering criteria:")
        if today:
            click.echo("   • Today only (overrides days)")
        elif days is not None:
            click.echo(f"   • Days: {days} (looking back {days} day{'s' if days != 1 else ''})")
        else:
            click.echo("   • Days: all open tasks (no date filtering)")
        click.echo(f"   • Status: {status}")
        if label:
            click.echo(f"   • Labels: {', '.join(label)}")
        else:
            # Show default label filter if no explicit labels provided
            default_label_filter = config.get_context_default_label_filter(current_context)
            if default_label_filter:
                click.echo(f"   • Default label filter: {default_label_filter}")
        if due:
            click.echo(f"   • Due date: {due}")
        weekdays_only = config.get_weekdays_only_lookback()
        if weekdays_only:
            click.echo("   • Weekdays only: True (Mon-Fri)")
        else:
            click.echo("   • Weekdays only: False (all days)")

        # Show current context
        click.echo(f"   • Context: {current_context}")
        click.echo()

    # Get tasks (include completed tasks for status filtering, filtered by context)
    tasks = task_manager.list_tasks(include_completed=True, context=current_context)

    # Apply date filtering first
    if today:
        # Override to show only today's tasks
        today_date = date.today()
        filtered_tasks = []
        for task in tasks:
            if task["completed_at"]:
                # For completed tasks, check if completed today
                completed_dt = datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00"))
                if completed_dt.date() == today_date:
                    filtered_tasks.append(task)
            else:
                # For open tasks, check if created today
                created_dt = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00"))
                if created_dt.date() == today_date:
                    filtered_tasks.append(task)
        tasks = filtered_tasks
    elif days is not None:
        # Apply days filtering only if days is specified
        weekdays_only = config.get_weekdays_only_lookback()
        tasks = filter_tasks_by_date_range(tasks, days=days, weekdays_only=weekdays_only)
    # If days is None, don't apply date filtering (show all tasks)

    # Apply status filtering
    if status in ["open", "o"]:
        tasks = [task for task in tasks if task["completed_at"] is None]
    elif status in ["completed", "done", "d"]:
        tasks = [task for task in tasks if task["completed_at"] is not None]
    # For "all" or "a", we keep all tasks (both open and completed)

    # Apply label filtering if requested
    if label:
        filtered_tasks = []
        for task in tasks:
            if task.get("labels"):
                # Clean up labels - remove empty strings and whitespace
                task_labels = [label.strip().lower() for label in task["labels"] if label.strip()]

                # Check if task matches any of the label criteria using boolean logic
                task_matches = False
                for label_criteria in label:
                    if evaluate_boolean_label_expression(task_labels, label_criteria):
                        task_matches = True
                        break

                if task_matches:
                    filtered_tasks.append(task)
        tasks = filtered_tasks
    else:
        # Apply default label filter for current context if no explicit labels provided
        default_label_filter = config.get_context_default_label_filter(current_context)
        if default_label_filter:
            filtered_tasks = []
            for task in tasks:
                task_labels = []
                if task.get("labels"):
                    # Clean up labels - remove empty strings and whitespace
                    task_labels = [label.strip().lower() for label in task["labels"] if label.strip()]

                # Apply the default label filter
                if evaluate_boolean_label_expression(task_labels, default_label_filter):
                    filtered_tasks.append(task)
            tasks = filtered_tasks

    # Apply due date filtering if requested
    if due:
        # DateParser and date imported at module level

        filtered_tasks = []
        for task in tasks:
            if not task.get("due_date"):
                continue  # Skip tasks without due dates

            task_matches = False

            if due == "overdue":
                task_matches = DateParser.is_overdue(task["due_date"])
            elif due == "today":
                task_matches = task["due_date"] == date.today().strftime("%Y-%m-%d")
            elif due == "week":
                # Due within next 7 days
                task_matches = DateParser.is_due_soon(task["due_date"], days=7)
            elif due == "month":
                # Due within next 30 days
                task_matches = DateParser.is_due_soon(task["due_date"], days=30)
            else:
                # Specific date format (YYYY-MM-DD)
                try:
                    # Keep parsing to validate format, but compare string equality to stored due_date
                    _ = datetime.strptime(due, "%Y-%m-%d").date()
                    task_matches = task["due_date"] == due
                except ValueError:
                    # Invalid date format, skip this filter
                    continue

            if task_matches:
                filtered_tasks.append(task)

        tasks = filtered_tasks

    # Display tasks
    if not tasks:
        click.echo("📝 No tasks found matching your criteria.")
        return

    # Organize tasks into sections
    # Important tasks (with #i) go in Important section, regardless of #t
    important_tasks = [task for task in tasks if is_important_task(task)]
    # Today tasks (with #t but not #i) go in Today section
    today_tasks = [task for task in tasks if is_today_task(task) and not is_important_task(task)]

    # Due date sections (only for open tasks)

    overdue_tasks = []
    due_soon_tasks = []
    due_today_tasks = []

    for task in tasks:
        if not task["completed_at"] and task.get("due_date"):  # Only open tasks with due dates
            if DateParser.is_overdue(task["due_date"]):
                overdue_tasks.append(task)
            elif task["due_date"] == date.today().strftime("%Y-%m-%d"):
                due_today_tasks.append(task)
            elif DateParser.is_due_soon(task["due_date"], days=3):
                due_soon_tasks.append(task)

    # Regular tasks (no #i or #t) go in Open section
    open_tasks = [task for task in tasks if not task["completed_at"] and not is_important_task(task) and not is_today_task(task) and not task.get("due_date")]  # Exclude tasks with due dates (they go in due date sections)

    # Completed tasks go in Completed section
    completed_tasks = [task for task in tasks if task["completed_at"] and not is_important_task(task) and not is_today_task(task)]

    # Display Important section
    if important_tasks:
        click.echo("Important")
        for i, task in enumerate(important_tasks, 1):
            formatted_task = format_task_for_display(task, config)
            click.echo(f"{formatted_task}")
        click.echo()

    # Display Today section
    if today_tasks:
        click.echo("Today")
        for i, task in enumerate(today_tasks, 1):
            formatted_task = format_task_for_display(task, config)
            click.echo(f"{formatted_task}")
        click.echo()

    # Display Overdue section
    if overdue_tasks:
        click.echo("🚨 Overdue")
        for task in overdue_tasks:
            formatted_task = format_task_for_display(task, config)
            click.echo(formatted_task)
        click.echo()

    # Display Due Soon section
    if due_soon_tasks:
        click.echo("⏰ Due Soon")
        for task in due_soon_tasks:
            formatted_task = format_task_for_display(task, config)
            click.echo(formatted_task)
        click.echo()

    # Display Due Today section
    if due_today_tasks:
        click.echo("📅 Due Today")
        for task in due_today_tasks:
            formatted_task = format_task_for_display(task, config)
            click.echo(formatted_task)
        click.echo()

    # Display Open section
    if open_tasks:
        click.echo("Open")
        for i, task in enumerate(open_tasks, 1):
            formatted_task = format_task_for_display(task, config)
            click.echo(f"{formatted_task}")
        click.echo()

    # Display Completed section
    if completed_tasks:
        click.echo("Completed")
        for task in completed_tasks:
            formatted_task = format_task_for_display(task, config)
            click.echo(formatted_task)


@cli.command(name="list-tasks")
@click.option("--days", "-d", default=1, help="Show tasks from the past N days (default: 1)")
@click.option("--today", "-t", is_flag=True, help="Show only today's tasks (overrides days)")
@click.option("--label", "-l", multiple=True, help="Filter by labels")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["open", "o", "completed", "done", "d", "all", "a"]),
    help="Filter by status (open/o, completed, done/d, all/a)",
)
@click.option(
    "--due",
    help="Filter by due date: specific date (YYYY-MM-DD), 'overdue', 'today', 'week', or 'month'",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show verbose output including database path and filtering details",
)
def list_tasks(days, label, today, status, due, verbose):
    """List tasks with optional filtering."""
    # Validate conflicting time filters
    if today and days != 1:  # days defaults to 1, so only conflict if explicitly set
        click.echo("❌ Error: Cannot use both --today and --days together")
        click.echo("   --today overrides --days, so they are mutually exclusive")
        click.echo("   Use either --today or --days N, but not both")
        return

    # Set verbose environment variable for DatabaseManager
    if verbose:
        os.environ["FIN_VERBOSE"] = "1"
    _list_tasks_impl(days, label, status, today, due, verbose)


@cli.command(name="list")
@click.option("--days", "-d", type=int, help="Show tasks from the past N days (default: show all open tasks)")
@click.option("--today", "-t", is_flag=True, help="Show only today's tasks (overrides days)")
@click.option("--label", "-l", multiple=True, help="Filter by labels")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["open", "o", "completed", "done", "d", "all", "a"]),
    default="open",
    help="Filter by status (open/o, completed, done/d, all/a)",
)
@click.option(
    "--due",
    help="Filter by due date: specific date (YYYY-MM-DD), 'overdue', 'today', 'week', or 'month'",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show verbose output including database path and filtering details",
)
def list_tasks_alias(days, label, today, status, due, verbose):
    """List tasks with optional filtering (alias for list-tasks)."""
    # Validate conflicting time filters
    if today and days is not None:
        click.echo("❌ Error: Cannot use both --today and --days together")
        click.echo("   --today overrides --days, so they are mutually exclusive")
        click.echo("   Use either --today or --days N, but not both")
        return

    # Set verbose environment variable for DatabaseManager
    if verbose:
        os.environ["FIN_VERBOSE"] = "1"
    _list_tasks_impl(days, label, status, today, due, verbose)


@cli.command(name="open-editor")
@click.option("--label", "-l", multiple=True, help="Filter by labels")
@click.option("--date", help="Filter by date (YYYY-MM-DD)")
@click.option("--all-tasks", is_flag=True, help="Show all tasks (including completed)")
@click.option("--dry-run", is_flag=True, help="Show what would be edited without opening editor")
def open_editor(label, date, all_tasks, dry_run):
    """Open tasks in your editor for editing completion status."""

    db_manager = _get_db_manager()
    editor_manager = EditorManager(db_manager)

    # Get tasks for editing (without opening editor)
    label_filter = label[0] if label else None
    tasks = editor_manager.get_tasks_for_editing(label=label_filter, target_date=date, all_tasks=all_tasks)

    if not tasks:
        click.echo("📝 No tasks found for editing.")
        return

    if dry_run:
        # Show what would be edited without opening the editor
        click.echo(f"📝 Found {len(tasks)} tasks for editing:")
        for task in tasks:
            status = "✓" if task.get("completed_at") else "□"
            click.echo(f"  {status} {task['content']}")
        click.echo("\nUse 'fin open-editor' (without --dry-run) to actually open the editor.")
        click.echo("💡 Tip: You can add new tasks by adding lines without #ref:task_XXX")
        return

    # Show what will be opened
    click.echo(f"📝 Opening {len(tasks)} tasks in editor...")
    click.echo("⚠️  This will open your default editor. Close the editor to save changes.")
    click.echo("💡 Tip: You can add new tasks by adding lines without #ref:task_XXX")

    # Only open editor at the very last moment when user explicitly requests it
    try:
        # Get the state before editing for comparison
        original_tasks = editor_manager.get_tasks_for_editing(label=label_filter, target_date=date, all_tasks=all_tasks)
        original_completed = [t for t in original_tasks if t.get("completed_at")]

        (
            completed_count,
            reopened_count,
            new_tasks_count,
            content_modified_count,
            deleted_count,
        ) = editor_manager.edit_tasks(label=label_filter, target_date=date, all_tasks=all_tasks)

        # Get the state after editing for detailed comparison
        updated_tasks = editor_manager.get_tasks_for_editing(label=label_filter, target_date=date, all_tasks=all_tasks)
        updated_completed = [t for t in updated_tasks if t.get("completed_at")]
        updated_open = [t for t in updated_tasks if not t.get("completed_at")]

        changes_made = completed_count > 0 or reopened_count > 0 or new_tasks_count > 0 or content_modified_count > 0 or deleted_count > 0

        if changes_made:
            click.echo("\n📊 Summary of Changes:")
            click.echo("=" * 40)

            # Show completed tasks
            if completed_count > 0:
                click.echo(f"✅ Completed ({completed_count}):")
                original_completed_ids = {t["id"] for t in original_completed}
                newly_completed = [t for t in updated_completed if t["id"] not in original_completed_ids]
                for task in newly_completed:
                    click.echo(f"  • {task['content']}")
                click.echo()

            # Show reopened tasks
            if reopened_count > 0:
                click.echo(f"🔄 Reopened ({reopened_count}):")
                newly_reopened = [t for t in updated_open if t["id"] in original_completed_ids]
                for task in newly_reopened:
                    click.echo(f"  • {task['content']}")
                click.echo()

            # Show new tasks
            if new_tasks_count > 0:
                click.echo(f"📝 Added ({new_tasks_count}):")
                # Get the most recent tasks that weren't in the original list
                all_tasks = editor_manager.task_manager.list_tasks(include_completed=True)
                original_ids = {t["id"] for t in original_tasks}
                new_tasks = [t for t in all_tasks if t["id"] not in original_ids]
                # Sort by creation time (newest first) and take the most recent ones
                new_tasks.sort(key=lambda x: x["created_at"], reverse=True)
                for task in new_tasks[:new_tasks_count]:
                    labels_str = f" [{', '.join(task['labels'])}]" if task["labels"] else ""
                    click.echo(f"  • {task['content']}{labels_str}")
                click.echo()

            # Show deleted tasks
            if deleted_count > 0:
                click.echo(f"🗑️  Deleted ({deleted_count}):")
                click.echo(f"  • {deleted_count} tasks removed from database")
                click.echo()

            # Show overall summary
            total_changes = completed_count + reopened_count + new_tasks_count + deleted_count
            click.echo(f"📈 Total changes: {total_changes}")

        else:
            click.echo("📝 No changes were made to tasks.")

    except RuntimeError as e:
        click.echo(f"❌ Error: {e}")
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")


def fine_command():
    """
    Fine command - alias for 'fin open-editor' that allows passing through arguments.

    This function creates a standalone command that acts as an alias for the open-editor
    functionality, allowing users to run 'fine' directly with the same options.

    IMPORTANT FOR TESTING:
    - Tests should NEVER call the actual editor (edit_tasks)
    - Tests should use parse_edited_content with text files to test parsing logic
    - See TESTING.md for the correct testing approach
    """
    import click

    # Create a standalone Click command
    @click.command(context_settings=dict(help_option_names=["-h", "--help"]))
    @click.option("--label", "-l", multiple=True, help="Filter by labels")
    @click.option("--date", help="Filter by date (YYYY-MM-DD)")
    @click.option(
        "--days",
        "-d",
        help="Show tasks from the past N days (including today). Use -d 0 for all time (limited by max_limit)",
    )
    @click.option(
        "--today",
        "-t",
        is_flag=True,
        help="Show only today's tasks (overrides days)",
    )
    @click.option(
        "--max-limit",
        default=100,
        help="Maximum number of tasks to show (default: 100)",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        help="Show what would be edited without opening editor",
    )
    @click.option(
        "--status",
        "-s",
        help=("Filter by status(es): open/o, completed, done/d, all/a, or " "comma-separated list like 'done,open' (default: open)"),
    )
    @click.option(
        "--verbose",
        "-v",
        is_flag=True,
        help="Show verbose output including database path and filtering details",
    )
    def fine_cli(label, date, days, max_limit, today, dry_run, status, verbose):
        """
        Edit tasks in your editor (alias for fin open-editor).

        Default behavior: Shows all open tasks (limited by max_limit)
        With -d N: Shows tasks from last N days (including today)
        With -d 0: Shows all tasks from all time (limited by max_limit)
        With -s done: Shows completed tasks instead of open ones
        With -s done,open: Shows both completed and open tasks
        """
        # Set verbose environment variable for DatabaseManager
        if verbose:
            os.environ["FIN_VERBOSE"] = "1"

        # Call the original open_editor function directly
        db_manager = _get_db_manager()
        editor_manager = EditorManager(db_manager)

        # Validate conflicting time filters
        if today and days is not None:
            click.echo("❌ Error: Cannot use both --today and --days together")
            click.echo("   --today overrides --days, so they are mutually exclusive")
            click.echo("   Use either --today or --days N, but not both")
            return

        # Parse status parameter (allow comma-separated values with flexible spacing)
        status_list = []
        if status:
            # Split by comma and strip whitespace
            status_list = [s.strip() for s in status.split(",")]
        else:
            # Default to open for fine command
            status_list = ["open"]

        # Show verbose information about filtering criteria
        if verbose:
            click.echo("🔍 Filtering criteria:")
            if today:
                click.echo("   • Today only (overrides days)")
            elif days is not None:
                days_int = int(days)
                if days_int == 0:
                    click.echo("   • Days: all time (no date restriction)")
                else:
                    click.echo(f"   • Days: {days_int} (looking back {days_int} day{'s' if days_int != 1 else ''})")
            else:
                click.echo("   • Days: all open tasks (no date restriction)")
            click.echo(f"   • Status: {', '.join(status_list)}")
            click.echo(f"   • Max limit: {max_limit}")
            if label:
                click.echo(f"   • Labels: {', '.join(label)}")
            if date:
                click.echo(f"   • Date: {date}")
            click.echo()

        # Get tasks for editing
        label_filter = label[0] if label else None

        # Get all tasks first, then apply status filtering
        all_tasks = editor_manager.task_manager.list_tasks(include_completed=True)

        # Apply status filtering first
        filtered_tasks = []
        for task in all_tasks:
            # Normalize status values to handle shorthand letters
            normalized_status_list = []
            for status in status_list:
                if status in ["o", "open"]:
                    normalized_status_list.append("open")
                elif status in ["d", "done"]:
                    normalized_status_list.append("done")
                elif status in ["a", "all"]:
                    normalized_status_list.append("all")
                elif status == "completed":
                    normalized_status_list.append("completed")
                else:
                    normalized_status_list.append(status)

            if "open" in normalized_status_list and task["completed_at"] is None:
                filtered_tasks.append(task)
            elif "completed" in normalized_status_list and task["completed_at"] is not None:
                filtered_tasks.append(task)
            elif "done" in normalized_status_list and task["completed_at"] is not None:
                filtered_tasks.append(task)
            elif "all" in normalized_status_list:
                filtered_tasks.append(task)

        # Now apply additional filters
        if today:
            # Override to show only today's tasks
            today_date = date.today()
            today_filtered_tasks = []
            for task in filtered_tasks:
                if task["completed_at"]:
                    # For completed tasks, check if completed today
                    completed_dt = datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00"))
                    if completed_dt.date() == today_date:
                        today_filtered_tasks.append(task)
                else:
                    # For open tasks, check if created today
                    created_dt = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00"))
                    if created_dt.date() == today_date:
                        today_filtered_tasks.append(task)
            filtered_tasks = today_filtered_tasks
        elif date:
            # For date-based filtering, filter by date after status filtering
            from fincli.utils import filter_tasks_by_date_range

            filtered_tasks = filter_tasks_by_date_range(filtered_tasks, target_date=date)
        elif label:
            # For label-based filtering, filter by label after status filtering
            label_filter = label[0] if label else None
            if label_filter:
                filtered_tasks = [t for t in filtered_tasks if t.get("labels") and label_filter in t["labels"]]
        elif days is not None:
            # For days-based filtering, apply date filtering after status filtering
            from fincli.utils import filter_tasks_by_date_range

            # Get weekdays_only configuration
            config = Config()
            weekdays_only = config.get_weekdays_only_lookback()

            # Convert days to integer (Click passes it as string)
            days_int = int(days)

            if days_int != 0:
                # Apply date filtering (days > 0)
                filtered_tasks = filter_tasks_by_date_range(filtered_tasks, days=days_int, weekdays_only=weekdays_only)

        # Apply max limit
        if len(filtered_tasks) > max_limit:
            if verbose:
                click.echo(f"⚠️  Warning: Found {len(filtered_tasks)} tasks, showing first {max_limit} due to max_limit")
            filtered_tasks = filtered_tasks[:max_limit]

        tasks = filtered_tasks

        if not tasks:
            click.echo("📝 No tasks found for editing.")
            return

        if dry_run:
            # Show what would be edited without opening the editor
            click.echo(f"📝 Found {len(tasks)} tasks for editing:")
            for task in tasks:
                status = "✓" if task.get("completed_at") else "□"
                click.echo(f"  {status} {task['content']}")
            click.echo("\nUse 'fine' (without --dry-run) to actually open the editor.")
            click.echo("💡 Tip: You can add new tasks by adding lines without #ref:task_XXX")
            return

        # Show what will be opened
        click.echo(f"📝 Opening {len(tasks)} tasks in editor...")
        click.echo("⚠️  This will open your default editor. Close the editor to save changes.")
        click.echo("💡 Tip: You can add new tasks by adding lines without #ref:task_XXX")

        # Only open editor at the very last moment when user explicitly requests it
        # NOTE: Tests should NEVER reach this point - they should use dry-run or test
        # the parsing logic directly with parse_edited_content
        try:
            # Get the state before editing for comparison
            original_tasks = tasks.copy()
            original_completed = [t for t in original_tasks if t.get("completed_at")]

            # Pass the already filtered tasks directly to avoid re-filtering
            (
                completed_count,
                reopened_count,
                new_tasks_count,
                content_modified_count,
                deleted_count,
            ) = editor_manager.edit_tasks_with_tasks(tasks)

            # Get the state after editing for detailed comparison
            # Use the same filtered tasks to maintain consistency with what was edited
            updated_tasks = tasks
            updated_completed = [t for t in updated_tasks if t.get("completed_at")]
            updated_open = [t for t in updated_tasks if not t.get("completed_at")]

            changes_made = completed_count > 0 or reopened_count > 0 or new_tasks_count > 0 or content_modified_count > 0 or deleted_count > 0

            if changes_made:
                click.echo("\n📊 Summary of Changes:")
                click.echo("=" * 40)

                # Show completed tasks
                if completed_count > 0:
                    click.echo(f"✅ Completed ({completed_count}):")
                    original_completed_ids = {t["id"] for t in original_completed}
                    newly_completed = [t for t in updated_completed if t["id"] not in original_completed_ids]
                    for task in newly_completed:
                        click.echo(f"  • {task['content']}")
                    click.echo()

                # Show reopened tasks
                if reopened_count > 0:
                    click.echo(f"🔄 Reopened ({reopened_count}):")
                    newly_reopened = [t for t in updated_open if t["id"] in original_completed_ids]
                    for task in newly_reopened:
                        click.echo(f"  • {task['content']}")
                    click.echo()

                # Show content modifications
                if content_modified_count > 0:
                    click.echo(f"✏️  Content Modified ({content_modified_count}):")
                    click.echo(f"  • {content_modified_count} tasks had their content updated")
                    click.echo()

                # Show new tasks
                if new_tasks_count > 0:
                    click.echo(f"📝 Added ({new_tasks_count}):")
                    # Get the most recent tasks that weren't in the original list
                    all_tasks = editor_manager.task_manager.list_tasks(include_completed=True)
                    original_ids = {t["id"] for t in original_tasks}
                    new_tasks = [t for t in all_tasks if t["id"] not in original_ids]
                    # Sort by creation time (newest first) and take the most recent ones
                    new_tasks.sort(key=lambda x: x["created_at"], reverse=True)
                    for task in new_tasks[:new_tasks_count]:
                        labels_str = f" [{', '.join(task['labels'])}]" if task["labels"] else ""
                        click.echo(f"  • {task['content']}{labels_str}")
                    click.echo()

                # Show deleted tasks
                if deleted_count > 0:
                    click.echo(f"🗑️  Deleted ({deleted_count}):")
                    click.echo(f"  • {deleted_count} tasks removed from database")
                    click.echo()

                # Show overall summary
                total_changes = completed_count + reopened_count + new_tasks_count + content_modified_count + deleted_count
                click.echo(f"📈 Total changes: {total_changes}")

            else:
                click.echo("📝 No changes were made to tasks.")

        except RuntimeError as e:
            click.echo(f"❌ Error: {e}")
        except Exception as e:
            click.echo(f"❌ Unexpected error: {e}")

    # Run the fine CLI
    fine_cli()


def fins_command():
    """
    Fins command - standalone command that shows tasks with defaults optimized for viewing completed tasks.

    This function creates a standalone command that shows tasks with a default behavior
    of showing completed tasks from the past week, which is useful for reviewing recent activity.
    """
    import sys

    import click

    # Create a standalone Click command
    @click.command(context_settings=dict(help_option_names=["-h", "--help"]))
    @click.argument("content", nargs=-1, required=False)
    @click.option(
        "--days",
        "-d",
        help="Show tasks from the past N days (including today). Use -d 0 for all time (limited by max_limit)",
    )
    @click.option(
        "--max-limit",
        default=100,
        help="Maximum number of tasks to show (default: 100)",
    )
    @click.option("--label", "-l", multiple=True, help="Filter by labels")
    @click.option(
        "--today",
        "-t",
        is_flag=True,
        help="Show only today's tasks (overrides default days behavior)",
    )
    @click.option(
        "--status",
        "-s",
        help=("Filter by status(es): open/o, completed, done/d, all/a, or " "comma-separated list like 'done,open' (default: completed)"),
    )
    @click.option(
        "--due",
        help="Filter by due date: specific date (YYYY-MM-DD), 'overdue', 'today', 'week', or 'month'",
    )
    @click.option(
        "--verbose",
        "-v",
        is_flag=True,
        help="Show verbose output including database path and filtering details",
    )
    def fins_cli(content, days, max_limit, label, today, status, due, verbose):
        """Query and display completed tasks, or add completed tasks."""
        # Set verbose environment variable for DatabaseManager
        if verbose:
            os.environ["FIN_VERBOSE"] = "1"

        # Parse status parameter (allow comma-separated values with flexible spacing)
        status_list = []
        if status:
            # Split by comma and strip whitespace
            status_list = [s.strip() for s in status.split(",")]
        else:
            # Default to completed for fins command
            status_list = ["completed"]

        # If content is provided, add it as a completed task
        if content:
            task_content = " ".join(content)
            db_manager = _get_db_manager()
            task_manager = TaskManager(db_manager)

            # Add the task as completed
            task_id = task_manager.add_task(task_content, labels=label, source="fins")

            # Mark it as completed immediately
            task_manager.update_task_completion(task_id, True)

            # Show success message with labels
            if label:
                labels_str = ", ".join(label)
                click.echo(f"✅ Task added and marked as completed: {task_content} [{labels_str}]")
            else:
                click.echo(f"✅ Task added and marked as completed: {task_content}")
            return

        # Otherwise, show tasks (existing behavior)
        db_manager = _get_db_manager()
        task_manager = TaskManager(db_manager)

        # Only show verbose information about filtering criteria when -v flag is used
        if verbose:
            click.echo("🔍 Filtering criteria:")
            if today:
                click.echo("   • Today only (overrides days)")
            elif days is not None:
                days_int = int(days)
                if days_int == 0:
                    click.echo("   • Days: all time (no date restriction)")
                else:
                    click.echo(f"   • Days: {days_int} (looking back {days_int} day{'s' if days_int != 1 else ''})")
            else:
                click.echo("   • Days: 2 (default: today and yesterday)")
            click.echo(f"   • Status: {', '.join(status_list)}")
            click.echo(f"   • Max limit: {max_limit}")
            if label:
                click.echo(f"   • Labels: {', '.join(label)}")
            if due:
                click.echo(f"   • Due date: {due}")

            # Show weekday configuration information
            config = Config()
            weekdays_only = config.get_weekdays_only_lookback()
            if weekdays_only:
                click.echo("   • Weekdays only: True (Mon-Fri)")
            else:
                click.echo("   • Weekdays only: False (all days)")
            click.echo()

        # Get tasks (include completed tasks for status filtering)
        tasks = task_manager.list_tasks(include_completed=True)

        # Apply date filtering first
        if today:
            # Override to show only today's tasks
            # Filter to only tasks completed today (not from last 1 day)
            today_date = date.today()
            filtered_tasks = []
            for task in tasks:
                if task["completed_at"]:
                    # For completed tasks, check if completed today
                    completed_dt = datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00"))
                    if completed_dt.date() == today_date:
                        filtered_tasks.append(task)
                else:
                    # For open tasks, check if created today
                    created_dt = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00"))
                    if created_dt.date() == today_date:
                        filtered_tasks.append(task)
            tasks = filtered_tasks
        elif days is not None:
            # User specified days
            days_int = int(days)
            config = Config()
            weekdays_only = config.get_weekdays_only_lookback()

            if days_int == 0:
                # -d 0 means all time, no date filtering
                pass  # Keep all tasks
            else:
                # Apply date filtering
                tasks = filter_tasks_by_date_range(tasks, days=days_int, weekdays_only=weekdays_only)
        else:
            # Default: show tasks from past 2 days
            config = Config()
            weekdays_only = config.get_weekdays_only_lookback()
            tasks = filter_tasks_by_date_range(tasks, days=2, weekdays_only=weekdays_only)

        # Apply status filtering
        filtered_tasks = []
        for task in tasks:
            # Normalize status values to handle shorthand letters
            normalized_status_list = []
            for status in status_list:
                if status in ["o", "open"]:
                    normalized_status_list.append("open")
                elif status in ["d", "done"]:
                    normalized_status_list.append("done")
                elif status in ["a", "all"]:
                    normalized_status_list.append("all")
                elif status == "completed":
                    normalized_status_list.append("completed")
                else:
                    normalized_status_list.append(status)

            if "open" in normalized_status_list and task["completed_at"] is None:
                filtered_tasks.append(task)
            elif "completed" in normalized_status_list and task["completed_at"] is not None:
                filtered_tasks.append(task)
            elif "done" in normalized_status_list and task["completed_at"] is not None:
                filtered_tasks.append(task)
            elif "all" in normalized_status_list:
                filtered_tasks.append(task)

        # Apply max limit
        total_tasks = len(filtered_tasks)
        if total_tasks > max_limit:
            if verbose:
                click.echo(f"⚠️  Warning: Found {total_tasks} tasks, showing first {max_limit} due to max_limit")
            filtered_tasks = filtered_tasks[:max_limit]

        # Apply label filtering if requested
        if label:
            # Simple label filtering - could be enhanced
            label_filtered_tasks = []
            for task in filtered_tasks:
                if task.get("labels"):
                    task_labels = [label.lower() for label in task["labels"]]
                    for requested_label in label:
                        if requested_label.lower() in task_labels:
                            label_filtered_tasks.append(task)
                            break
            filtered_tasks = label_filtered_tasks

        # Apply due date filtering if requested
        if due:

            due_filtered_tasks = []
            for task in filtered_tasks:
                if not task.get("due_date"):
                    continue  # Skip tasks without due dates

                task_matches = False

                if due == "overdue":
                    task_matches = DateParser.is_overdue(task["due_date"])
                elif due == "today":
                    task_matches = task["due_date"] == date.today().strftime("%Y-%m-%d")
                elif due == "week":
                    # Due within next 7 days
                    task_matches = DateParser.is_due_soon(task["due_date"], days=7)
                elif due == "month":
                    # Due within next 30 days
                    task_matches = DateParser.is_due_soon(task["due_date"], days=30)
                else:
                    # Specific date format (YYYY-MM-DD)
                    try:
                        _ = datetime.strptime(due, "%Y-%m-%d").date()
                        task_matches = task["due_date"] == due
                    except ValueError:
                        # Invalid date format, skip this filter
                        continue

                if task_matches:
                    due_filtered_tasks.append(task)

            filtered_tasks = due_filtered_tasks

        # Display tasks
        if not filtered_tasks:
            click.echo("📝 No tasks found matching your criteria.")
            return

        # Default behavior: just show the tasks cleanly
        # Verbose mode: show with additional context
        for task in filtered_tasks:
            if verbose:
                # Show with full formatting including task ID
                formatted_task = format_task_for_display(task)
                click.echo(formatted_task)
            else:
                # Show clean format without task ID - just the essential info
                status_symbol = "[x]" if task.get("completed_at") else "[ ]"
                content = task["content"]

                # Add completion date for completed tasks
                date_display = ""
                if task.get("completed_at"):
                    try:
                        completed_dt = datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00"))
                        date_display = f" {completed_dt.strftime('%Y-%m-%d')}"
                    except (ValueError, TypeError):
                        # Fallback if date parsing fails
                        date_display = ""

                labels_display = ""
                if task.get("labels"):
                    hashtags = [f"#{label}" for label in task["labels"]]
                    labels_display = f"  {','.join(hashtags)}"

                click.echo(f"{status_symbol}{date_display} {content}{labels_display}")

    # Run the fins CLI
    fins_cli()


@cli.command(name="close")
@click.argument("task_identifier", nargs=-1)
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def close_task(task_identifier, verbose):
    """Mark task(s) as completed by ID or content pattern."""
    if not task_identifier:
        click.echo("❌ Error: Please specify task ID(s) or content pattern")
        click.echo("   Examples: fin close 1")
        click.echo("            fin close 'flight'")
        click.echo("            fin close 1 2 3")
        return

    # Set verbose environment variable for DatabaseManager
    if verbose:
        os.environ["FIN_VERBOSE"] = "1"

    db_manager = _get_db_manager()
    task_manager = TaskManager(db_manager)

    # Get all tasks to search through
    all_tasks = task_manager.list_tasks(include_completed=True)

    completed_count = 0

    for identifier in task_identifier:
        # Try to parse as integer (task ID)
        try:
            task_id = int(identifier)
            # Find task by ID
            task = next((task for task in all_tasks if task["id"] == task_id), None)
            if task:
                if task["completed_at"]:
                    click.echo(f"⚠️  Task {task_id} is already completed")
                else:
                    task_manager.update_task_completion(task_id, True)
                    click.echo(f"✅ Marked task {task_id} as completed: {task['content']}")
                    completed_count += 1
            else:
                click.echo(f"❌ Task {task_id} not found")
        except ValueError:
            # Treat as content pattern
            matching_tasks = [task for task in all_tasks if identifier.lower() in task["content"].lower() and not task["completed_at"]]
            if matching_tasks:
                # Take the first matching task
                task = matching_tasks[0]
                task_manager.update_task_completion(task["id"], True)
                click.echo(f"✅ Marked task {task['id']} as completed: {task['content']}")
                completed_count += 1
            else:
                click.echo(f"❌ No open tasks found containing '{identifier}'")

    if completed_count > 0:
        click.echo(f"🎉 Completed {completed_count} task(s)")


@cli.command(name="toggle")
@click.argument("task_identifier", nargs=-1)
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def toggle_task(task_identifier, verbose):
    """Toggle task completion status by ID."""
    if not task_identifier:
        click.echo("❌ Error: Please specify task ID(s)")
        click.echo("   Examples: fin toggle 1")
        click.echo("            fin toggle 1 2 3")
        return

    # Set verbose environment variable for DatabaseManager
    if verbose:
        os.environ["FIN_VERBOSE"] = "1"

    db_manager = _get_db_manager()
    task_manager = TaskManager(db_manager)

    # Get all tasks to search through
    all_tasks = task_manager.list_tasks(include_completed=True)

    toggled_count = 0

    for identifier in task_identifier:
        # Try to parse as integer (task ID)
        try:
            task_id = int(identifier)
            # Find task by ID
            task = next((task for task in all_tasks if task["id"] == task_id), None)
            if task:
                new_status = not task["completed_at"]
                task_manager.update_task_completion(task_id, new_status)
                status_text = "completed" if new_status else "reopened"
                click.echo(f"✅ {status_text.title()} task {task_id}: {task['content']}")
                toggled_count += 1
            else:
                click.echo(f"❌ Task {task_id} not found")
        except ValueError:
            click.echo(f"❌ Error: '{identifier}' is not a valid task ID (must be a number)")

    if toggled_count > 0:
        click.echo(f"🎉 Toggled {toggled_count} task(s)")


@cli.command(name="t")
@click.argument("task_identifier", nargs=-1)
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def toggle_alias(task_identifier, verbose):
    """Alias for toggle command."""
    # Call the toggle logic directly
    if not task_identifier:
        click.echo("❌ Error: Please specify task ID(s)")
        click.echo("   Examples: fin t 1")
        click.echo("            fin t 1 2 3")
        return

    # Set verbose environment variable for DatabaseManager
    if verbose:
        os.environ["FIN_VERBOSE"] = "1"

    db_manager = _get_db_manager()
    task_manager = TaskManager(db_manager)

    # Get all tasks to search through
    all_tasks = task_manager.list_tasks(include_completed=True)

    toggled_count = 0

    for identifier in task_identifier:
        # Parse as integer (task ID)
        try:
            task_id = int(identifier)
            # Find task by ID
            task = next((task for task in all_tasks if task["id"] == task_id), None)
            if task:
                new_status = not task["completed_at"]
                task_manager.update_task_completion(task_id, new_status)
                status_text = "completed" if new_status else "reopened"
                click.echo(f"✅ {status_text.title()} task {task_id}: {task['content']}")
                toggled_count += 1
            else:
                click.echo(f"❌ Task {task_id} not found")
        except ValueError:
            click.echo(f"❌ Error: '{identifier}' is not a valid task ID (must be a number)")

    if toggled_count > 0:
        click.echo(f"🎉 Toggled {toggled_count} task(s)")


@cli.command(name="list-labels")
def list_labels():
    """List all known labels."""
    db_manager = _get_db_manager()
    label_manager = LabelManager(db_manager)

    labels = label_manager.get_all_labels()

    if not labels:
        click.echo("No labels found in any tasks")
        return

    click.echo("Known labels:")
    for label in sorted(labels):
        click.echo(f"- {label}")


@cli.command(name="backup")
@click.option("--description", "-d", help="Description of what changed")
def create_backup(description):
    """Create a backup of the current database."""
    db_manager = _get_db_manager()
    backup_manager = DatabaseBackup(db_manager.db_path)

    backup_id = backup_manager.create_backup(description or "Manual backup")

    if backup_id > 0:
        click.echo(f"✅ Backup created: backup_{backup_id:03d}")
    else:
        click.echo("❌ No database found to backup")


@cli.command(name="list-backups")
def list_backups():
    """List all available backups."""
    db_manager = _get_db_manager()
    backup_manager = DatabaseBackup(db_manager.db_path)

    backups = backup_manager.list_backups()

    if not backups:
        click.echo("No backups found")
        return

    click.echo("Available backups:")
    for backup in backups:
        timestamp = backup["timestamp"][:19]  # Truncate to seconds
        click.echo(f"  backup_{backup['backup_id']:03d}: {timestamp} ({backup['task_count']} tasks)")
        if backup.get("description"):
            click.echo(f"    Description: {backup['description']}")


@cli.command(name="restore")
@click.argument("backup_id", type=int)
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt (alias for --force)")
def restore_backup(backup_id, force, yes):
    """Restore database from a backup."""
    db_manager = _get_db_manager()
    backup_manager = DatabaseBackup(db_manager.db_path)

    skip_confirmation = force or yes

    if not skip_confirmation:
        click.echo(f"⚠️  This will overwrite your current database with backup_{backup_id:03d}")
        click.echo("💡 Use --force or --yes to skip this confirmation")
        if not click.confirm("Proceed with restore?"):
            click.echo("Restore cancelled.")
            return

    if backup_manager.rollback(backup_id):
        click.echo(f"✅ Successfully restored from backup_{backup_id:03d}")
    else:
        click.echo(f"❌ Failed to restore from backup_{backup_id:03d}")


@cli.command(name="restore-latest")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt (alias for --force)")
def restore_latest_backup(force, yes):
    """Restore database from the latest backup."""
    db_manager = _get_db_manager()
    backup_manager = DatabaseBackup(db_manager.db_path)

    latest_id = backup_manager.get_latest_backup_id()
    if latest_id is None:
        click.echo("❌ No backups found")
        return

    skip_confirmation = force or yes

    if not skip_confirmation:
        click.echo(f"⚠️  This will overwrite your current database with backup_{latest_id:03d}")
        click.echo("💡 Use --force or --yes to skip this confirmation")
        if not click.confirm("Proceed with restore?"):
            click.echo("Restore cancelled.")
            return

    if backup_manager.restore_latest():
        click.echo(f"✅ Successfully restored from backup_{latest_id:03d}")
    else:
        click.echo(f"❌ Failed to restore from backup_{latest_id:03d}")


@cli.command(name="export")
@click.argument("file_path", type=click.Path())
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "json", "txt"]),
    default="csv",
    help="Export format",
)
@click.option(
    "--include-completed",
    is_flag=True,
    default=True,
    help="Include completed tasks (default: True)",
)
def export_tasks(file_path, format, include_completed):
    """Export all tasks to a flat file."""
    db_manager = _get_db_manager()
    task_manager = TaskManager(db_manager)

    # Get all tasks
    tasks = task_manager.list_tasks(include_completed=include_completed)

    if not tasks:
        click.echo("📝 No tasks found to export.")
        return

    try:
        if format == "csv":
            _export_csv(tasks, file_path)
        elif format == "json":
            _export_json(tasks, file_path)
        elif format == "txt":
            _export_txt(tasks, file_path)

        click.echo(f"✅ Exported {len(tasks)} tasks to {file_path}")

    except Exception as e:
        click.echo(f"❌ Export failed: {e}")
        raise click.Abort()


def _export_csv(tasks, file_path):
    """Export tasks to CSV format."""
    import csv

    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "ID",
            "Content",
            "Status",
            "Created",
            "Completed",
            "Labels",
            "Source",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for task in tasks:
            status = "completed" if task["completed_at"] else "open"
            labels = ",".join(task.get("labels", [])) if task.get("labels") else ""

            writer.writerow(
                {
                    "ID": task["id"],
                    "Content": task["content"],
                    "Status": status,
                    "Created": task["created_at"],
                    "Completed": task["completed_at"] or "",
                    "Labels": labels,
                    "Source": task.get("source", "cli"),
                }
            )


def _export_json(tasks, file_path):
    """Export tasks to JSON format."""
    import json

    # Convert tasks to serializable format
    export_data = []
    for task in tasks:
        export_task = {
            "id": task["id"],
            "content": task["content"],
            "status": "completed" if task["completed_at"] else "open",
            "created_at": task["created_at"],
            "completed_at": task["completed_at"],
            "labels": task.get("labels", []),
            "source": task.get("source", "cli"),
        }
        export_data.append(export_task)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)


def _export_txt(tasks, file_path):
    """Export tasks to plain text format using editor format."""
    from fincli.editor import EditorManager

    db_manager = _get_db_manager()
    editor_manager = EditorManager(db_manager)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# FinCLI Task Export - {len(tasks)} tasks\n")
        f.write(f"# Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for task in tasks:
            # Use the same formatting as the editor
            task_line = editor_manager._format_task_with_reference(task)
            f.write(f"{task_line}\n")


@cli.command(name="import")
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "json", "txt"]),
    help="Import format (auto-detected if not specified)",
)
@click.option("--label", "-l", multiple=True, help="Add labels to imported tasks")
@click.option("--clear-existing", is_flag=True, help="Clear existing tasks before import")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt (alias for --force)")
def import_tasks_from_file(file_path, format, label, clear_existing, force, yes):
    """Import tasks from a flat file."""
    db_manager = _get_db_manager()
    task_manager = TaskManager(db_manager)

    # Auto-detect format if not specified
    if not format:
        if file_path.endswith(".csv"):
            format = "csv"
        elif file_path.endswith(".json"):
            format = "json"
        elif file_path.endswith(".txt"):
            format = "txt"
        else:
            click.echo("❌ Could not auto-detect format. Please specify --format")
            raise click.Abort()

    # Combine force and yes flags
    skip_confirmation = force or yes

    # Show import preview
    if not skip_confirmation:
        preview = _get_import_preview(file_path, format, label, clear_existing)
        click.echo(preview)

        # Only prompt for confirmation if it's a destructive operation
        if clear_existing:
            if not click.confirm("⚠️  This will DELETE ALL existing tasks. Proceed?"):
                click.echo("Import cancelled.")
                return
        else:
            # For non-destructive imports, just proceed without confirmation
            click.echo("💡 Use --force or --yes to skip this preview in the future")

    try:
        if clear_existing:
            # Clear existing tasks
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tasks")
                conn.commit()
            click.echo("🗑️  Cleared existing tasks")

        imported_count = 0

        if format == "csv":
            imported_count = _import_csv(task_manager, file_path, label)
        elif format == "json":
            imported_count = _import_json(task_manager, file_path, label)
        elif format == "txt":
            imported_count = _import_txt(task_manager, file_path, label)

        click.echo(f"✅ Successfully imported {imported_count} tasks from {file_path}")

    except Exception as e:
        click.echo(f"❌ Import failed: {e}")
        raise click.Abort()


def _get_import_preview(file_path, format, additional_labels, clear_existing):
    """Generate a preview of what the import will do."""
    preview_lines = []
    preview_lines.append(f"📋 Import Preview for {file_path}")
    preview_lines.append(f"📁 Format: {format}")
    preview_lines.append(f"🏷️  Additional labels: {', '.join(additional_labels) if additional_labels else 'none'}")
    preview_lines.append(f"🗑️  Clear existing: {'Yes' if clear_existing else 'No'}")
    preview_lines.append("")

    # Count tasks in file
    task_count = 0
    completed_count = 0

    try:
        if format == "csv":
            import csv

            with open(file_path, "r", newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row.get("Content", "").strip():
                        task_count += 1
                        if row.get("Status") == "completed":
                            completed_count += 1

        elif format == "json":
            import json

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for task_data in data:
                    if task_data.get("content", "").strip():
                        task_count += 1
                        if task_data.get("status") == "completed":
                            completed_count += 1

        elif format == "txt":
            from fincli.editor import EditorManager

            db_manager = _get_db_manager()
            editor_manager = EditorManager(db_manager)

            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    task_info = editor_manager.parse_task_line(line)
                    if task_info and task_info["content"].strip():
                        task_count += 1
                        if task_info["is_completed"]:
                            completed_count += 1

        preview_lines.append(f"📊 File contains: {task_count} tasks ({completed_count} completed)")

        # Show current database stats
        db_manager = _get_db_manager()
        task_manager = TaskManager(db_manager)
        current_tasks = task_manager.list_tasks(include_completed=True)
        current_count = len(current_tasks)
        current_completed = len([t for t in current_tasks if t["completed_at"]])

        preview_lines.append(f"📊 Current database: {current_count} tasks ({current_completed} completed)")

        if clear_existing:
            preview_lines.append("⚠️  WARNING: All existing tasks will be deleted!")
        else:
            preview_lines.append(f"➕ {task_count} new tasks will be added")

    except Exception as e:
        preview_lines.append(f"❌ Error reading file: {e}")

    return "\n".join(preview_lines)


def _import_csv(task_manager, file_path, additional_labels):
    """Import tasks from CSV format."""
    import csv

    imported_count = 0

    with open(file_path, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            content = row.get("Content", "").strip()
            if not content:
                continue

            # Parse labels
            labels = []
            if row.get("Labels"):
                labels.extend([label.strip() for label in row["Labels"].split(",") if label.strip()])

            # Add additional labels
            labels.extend(additional_labels)

            # Add task
            task_manager.add_task(content, labels, source="csv-import")
            imported_count += 1

    return imported_count


def _import_json(task_manager, file_path, additional_labels):
    """Import tasks from JSON format."""
    import json

    imported_count = 0

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for task_data in data:
        content = task_data.get("content", "").strip()
        if not content:
            continue

        # Parse labels
        labels = task_data.get("labels", [])
        labels.extend(additional_labels)

        # Add task
        task_id = task_manager.add_task(content, labels, source="json-import")
        imported_count += 1

        # Mark as completed if it was completed in the export
        if task_data.get("status") == "completed" and task_data.get("completed_at"):
            task_manager.update_task_completion(task_id, True)

    return imported_count


def _import_txt(task_manager, file_path, additional_labels):
    """Import tasks from plain text format using editor parsing."""
    from fincli.editor import EditorManager

    db_manager = _get_db_manager()
    editor_manager = EditorManager(db_manager)

    imported_count = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Use the same parsing logic as the editor
            task_info = editor_manager.parse_task_line(line)
            if not task_info:
                continue

            # Skip empty tasks
            if not task_info["content"].strip():
                continue

            # Add additional labels
            labels = task_info.get("labels", [])
            labels.extend(additional_labels)

            # Add task
            task_id = task_manager.add_task(task_info["content"], labels, source="txt-import")
            imported_count += 1

            # Mark as completed if it was completed in the export
            if task_info["is_completed"]:
                task_manager.update_task_completion(task_id, True)

    return imported_count


@cli.command(name="digest")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "markdown", "html", "csv"]),
    default="text",
    help="Output format",
)
@click.option(
    "--period",
    type=click.Choice(["daily", "weekly", "monthly"]),
    default="daily",
    help="Report period",
)
def digest(output_format, period):
    """Generate a digest report."""
    db_manager = _get_db_manager()
    analytics_manager = AnalyticsManager(db_manager)

    report = analytics_manager.generate_digest(period, output_format)
    click.echo(report)


@cli.command(name="report")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "markdown", "html", "csv"]),
    default="text",
    help="Output format",
)
@click.option(
    "--period",
    type=click.Choice(["daily", "weekly", "monthly"]),
    default="weekly",
    help="Report period",
)
@click.option("--output", help="Output file path")
@click.option("--overdue", is_flag=True, help="Show only overdue tasks")
def report(output_format, period, output, overdue):
    """Generate a detailed analytics report."""
    db_manager = _get_db_manager()
    analytics_manager = AnalyticsManager(db_manager)

    if overdue:
        # For now, use digest with overdue flag
        report_content = analytics_manager.generate_digest("daily", output_format)
    else:
        report_content = analytics_manager.generate_digest(period, output_format)

    if output:
        with open(output, "w") as f:
            f.write(report_content)
    else:
        click.echo(report_content)


@cli.command(name="context")
@click.argument("action", type=click.Choice(["list", "create", "delete", "set-default", "show"]))
@click.argument("name", required=False)
@click.option("--description", help="Description for new context")
@click.option("--force", is_flag=True, help="Force deletion of context with tasks")
def context_command(action, name, description, force):
    """Manage task contexts."""
    db_manager = _get_db_manager()

    if action == "list":
        contexts = ContextManager.list_contexts(db_manager)
        click.echo("📁 Available contexts:")
        for context in contexts:
            if context == ContextManager.DEFAULT_CONTEXT:
                click.echo(f"  • {context} (default)")
            else:
                click.echo(f"  • {context}")

    elif action == "create":
        if not name:
            click.echo("❌ Context name is required for creation")
            sys.exit(1)
        try:
            # Create context by adding a task with that context
            task_manager = TaskManager(db_manager)
            task_id = task_manager.add_task(f"Context initialization task for {name}", [], "system", None, name)
            # Delete the initialization task
            task_manager.delete_task(task_id)
            click.echo(f"✅ Context '{name}' created successfully")
        except ValueError as e:
            click.echo(f"❌ Error: {e}")
            sys.exit(1)

    elif action == "delete":
        if not name:
            click.echo("❌ Context name is required for deletion")
            sys.exit(1)
        if name == ContextManager.DEFAULT_CONTEXT:
            click.echo("❌ Cannot delete default context")
            sys.exit(1)

        # Check if context has tasks
        task_manager = TaskManager(db_manager)
        tasks = task_manager.list_tasks(include_completed=True, context=name)
        if tasks and not force:
            click.echo(f"❌ Context '{name}' has {len(tasks)} tasks")
            click.echo("Use --force to delete anyway, or reassign tasks first")
            sys.exit(1)

        # Delete tasks in context
        for task in tasks:
            task_manager.delete_task(task["id"])

        click.echo(f"✅ Context '{name}' deleted successfully")

    elif action == "set-default":
        if not name:
            click.echo("❌ Context name is required for set-default")
            sys.exit(1)
        # This would update config, but for now just show message
        click.echo(f"ℹ️  Default context would be set to '{name}' (not yet implemented)")

    elif action == "show":
        if not name:
            click.echo("❌ Context name is required for show")
            sys.exit(1)
        task_manager = TaskManager(db_manager)
        tasks = task_manager.list_tasks(include_completed=True, context=name)
        click.echo(f"📁 Context: {name}")
        click.echo(f"📊 Total tasks: {len(tasks)}")
        open_tasks = [t for t in tasks if not t["completed_at"]]
        click.echo(f"📝 Open tasks: {len(open_tasks)}")
        completed_tasks = [t for t in tasks if t["completed_at"]]
        click.echo(f"✅ Completed tasks: {len(completed_tasks)}")


@cli.command(name="context-label-filter")
@click.argument("action", type=click.Choice(["set", "get", "remove", "list"]))
@click.argument("context", required=False)
@click.option("--filter", help="Label filter expression (e.g., 'NOT backlog')")
def context_label_filter_command(action, context, filter):
    """Manage default label filters for contexts."""
    config = Config()

    if action == "set":
        if not context or not filter:
            click.echo("❌ Both context and filter are required for setting")
            click.echo("Example: fin context-label-filter set default 'NOT backlog'")
            sys.exit(1)

        try:
            config.set_context_default_label_filter(context, filter)
            click.echo(f"✅ Set default label filter for context '{context}': {filter}")
        except Exception as e:
            click.echo(f"❌ Error setting filter: {e}")
            sys.exit(1)

    elif action == "get":
        if not context:
            click.echo("❌ Context name is required for getting filter")
            sys.exit(1)

        default_filter = config.get_context_default_label_filter(context)
        if default_filter:
            click.echo(f"📁 Context '{context}' default label filter: {default_filter}")
        else:
            click.echo(f"📁 Context '{context}' has no default label filter")

    elif action == "remove":
        if not context:
            click.echo("❌ Context name is required for removing filter")
            sys.exit(1)

        config.remove_context_default_label_filter(context)
        click.echo(f"✅ Removed default label filter for context '{context}'")

    elif action == "list":
        all_filters = config.get_all_context_default_label_filters()
        if all_filters:
            click.echo("📁 Context default label filters:")
            for ctx, filt in all_filters.items():
                click.echo(f"  • {ctx}: {filt}")
        else:
            click.echo("📁 No context default label filters configured")


@cli.command(name="config")
@click.option("--auto-today", type=bool, help="Auto-add today label to important tasks")
@click.option("--show-sections", type=bool, help="Show organized sections in task lists")
@click.option("--default-days", type=int, help="Default number of days for task lists")
@click.option("--default-editor", help="Default editor for task editing")
@click.option(
    "--show-all-open",
    type=bool,
    help="Show all open tasks by default (vs. just recent ones)",
)
@click.option(
    "--weekdays-only",
    type=bool,
    help="Count only weekdays (Monday-Friday) for date lookback",
)
@click.option(
    "--task-title-wrap-width",
    type=int,
    help="Width for wrapping long task titles (0 to disable)",
)
@click.option(
    "--task-date-format",
    help="Date format for task display (e.g., M/D, MM/DD, MM-DD)",
)
def config_command(
    auto_today,
    show_sections,
    default_days,
    default_editor,
    show_all_open,
    weekdays_only,
    task_title_wrap_width,
    task_date_format,
):
    """Manage FinCLI configuration."""
    config = Config()

    if auto_today is not None:
        config.set_auto_today_for_important(auto_today)
        click.echo(f"✅ Auto-today for important tasks: {auto_today}")

    if show_sections is not None:
        config.set_show_sections(show_sections)
        click.echo(f"✅ Show organized sections: {show_sections}")

    if default_days is not None:
        config.set_default_days(default_days)
        click.echo(f"✅ Default days: {default_days}")

    if default_editor is not None:
        config.set_default_editor(default_editor)
        click.echo(f"✅ Default editor: {default_editor}")

    if show_all_open is not None:
        config.set_show_all_open_by_default(show_all_open)
        click.echo(f"✅ Show all open tasks by default: {show_all_open}")

    if weekdays_only is not None:
        config.set_weekdays_only_lookback(weekdays_only)
        click.echo(f"✅ Weekdays only lookback: {weekdays_only}")

    if task_title_wrap_width is not None:
        config.set_task_title_wrap_width(task_title_wrap_width)
        click.echo(f"✅ Task title wrap width: {task_title_wrap_width}")

    if task_date_format is not None:
        config.set_task_date_format(task_date_format)
        click.echo(f"✅ Task date format: {task_date_format}")

    # Show current configuration
    if all(
        param is None
        for param in [
            auto_today,
            show_sections,
            default_days,
            default_editor,
            show_all_open,
            weekdays_only,
            task_title_wrap_width,
            task_date_format,
        ]
    ):
        click.echo("📋 Current Configuration:")
        click.echo(f"  Auto-today for important tasks: {config.get_auto_today_for_important()}")
        click.echo(f"  Show organized sections: {config.get_show_sections()}")
        click.echo(f"  Default days: {config.get_default_days()}")
        click.echo(f"  Default editor: {config.get_default_editor() or 'system default'}")
        click.echo(f"  Show all open tasks by default: {config.get_show_all_open_by_default()}")
        click.echo(f"  Weekdays only lookback: {config.get_weekdays_only_lookback()}")
        click.echo(f"  Task title wrap width: {config.get_task_title_wrap_width()}")
        click.echo(f"  Task date format: {config.get_task_date_format()}")
        click.echo(f"  Config file: {config.config_file}")


def main():
    """Main entry point that handles direct task addition."""
    args = sys.argv[1:]

    # Check for Click-specific flags that should always be handled by Click
    if args and any(arg in ["--help", "-h", "--version"] for arg in args):
        # Normal Click processing for help and version flags
        cli()
        return

    # Check for Click commands that should always be handled by Click
    click_commands = ["context", "config", "backup", "restore", "import", "export", "digest", "report", "sync-sheets", "sync-status", "t", "toggle", "close"]
    if args and args[0] in click_commands:
        # Normal Click processing for these commands
        cli()
        return

    # Check for verbose flag (which we handle specially)
    verbose = "--verbose" in args or "-v" in args

    # Check for days flag (-d) when used standalone
    days_arg = None
    if args and "-d" in args:
        try:
            d_index = args.index("-d")
            if d_index + 1 < len(args) and args[d_index + 1].isdigit():
                days_arg = int(args[d_index + 1])
                # Remove the -d and its value from args for further processing
                args = args[:d_index] + args[d_index + 2 :]
        except (ValueError, IndexError):
            pass

    # If no arguments provided or only verbose/days flags, default to list behavior
    if not args or (args and all(arg in ["--verbose", "-v"] for arg in args)):
        if verbose:
            os.environ["FIN_VERBOSE"] = "1"

        db_manager = _get_db_manager()
        task_manager = TaskManager(db_manager)
        config = Config()

        # Determine whether to show all open tasks or just recent ones
        show_all_open = config.get_show_all_open_by_default()

        # If days flag was specified, override the default behavior
        if days_arg is not None:
            show_all_open = False

        # Set max limit for open tasks
        max_limit = 100

        if show_all_open:
            # Show all open tasks (no date filtering)
            tasks = task_manager.list_tasks(include_completed=True)
            tasks = [task for task in tasks if task["completed_at"] is None]

            # Apply max limit and show warning if needed
            total_tasks = len(tasks)
            if total_tasks > max_limit:
                click.echo(f"⚠️  Warning: Found {total_tasks} open tasks, showing first {max_limit} due to max_limit")
                tasks = tasks[:max_limit]

            if verbose:
                click.echo("🔍 Default filtering criteria:")
                click.echo("   • Status: open (all open tasks)")
                click.echo(f"   • Max limit: {max_limit}")
                click.echo(f"   • Tasks matching filters: {len(tasks)}")
                if total_tasks > max_limit:
                    click.echo(f"   • Total available: {total_tasks}")

                # Show current context
                current_context = ContextManager.get_current_context()
                click.echo(f"   • Context: {current_context}")
                click.echo()
        else:
            # Show recent open tasks (default behavior or days-specified)
            days = days_arg if days_arg is not None else config.get_default_days()
            weekdays_only = config.get_weekdays_only_lookback()
            tasks = task_manager.list_tasks(include_completed=True)
            tasks = filter_tasks_by_date_range(tasks, days=days, weekdays_only=weekdays_only)
            tasks = [task for task in tasks if task["completed_at"] is None]

            if verbose:
                click.echo("🔍 Default filtering criteria:")
                if days_arg is not None:
                    click.echo(f"   • Days: {days} (looking back {days} day{'s' if days != 1 else ''})")
                else:
                    click.echo(f"   • Days: {days} (looking back {days} day{'s' if days != 1 else ''})")
                click.echo("   • Status: open")
                click.echo(f"   • Tasks matching filters: {len(tasks)}")
                if weekdays_only:
                    click.echo("   • Weekdays only: True (Mon-Fri)")
                else:
                    click.echo("   • Weekdays only: False (all days)")

                # Show current context
                current_context = ContextManager.get_current_context()
                click.echo(f"   • Context: {current_context}")
                click.echo()

        if not tasks:
            if show_all_open:
                click.echo("📝 No open tasks found.")
            else:
                days = days_arg if days_arg is not None else config.get_default_days()
                click.echo(f"📝 No open tasks found for the past {days} day{'s' if days != 1 else ''}.")
            click.echo("💡 Try adding a task: fin 'your task here'")
            click.echo("💡 Or see all commands: fin --help")
            return
        else:
            # Organize tasks into sections
            important_tasks = [task for task in tasks if is_important_task(task)]
            today_tasks = [task for task in tasks if is_today_task(task) and not is_important_task(task)]
            open_tasks = [task for task in tasks if not is_important_task(task) and not is_today_task(task)]

            # Display Important section
            if important_tasks:
                click.echo("Important")
                for i, task in enumerate(important_tasks, 1):
                    formatted_task = format_task_for_display(task, config)
                    click.echo(f"{formatted_task}")
                click.echo()

            # Display Today section
            if today_tasks:
                click.echo("Today")
                for i, task in enumerate(today_tasks, 1):
                    formatted_task = format_task_for_display(task, config)
                    click.echo(f"{formatted_task}")
                click.echo()

            # Display Open section
            if open_tasks:
                click.echo("Open")
                for i, task in enumerate(open_tasks, 1):
                    formatted_task = format_task_for_display(task, config)
                    click.echo(f"{formatted_task}")
            return

    # If we get here, we have arguments that should be treated as a direct task addition
    # Check if this is a direct task addition (no subcommand)
    if (
        args
        and not args[0].startswith("-")
        and args[0]
        not in [
            "add-task",
            "add",
            "init",
            "list-tasks",
            "list",
            "open-editor",
            "complete",
            "done",
            "reopen",
            "toggle",
            "list-labels",
            "import",
            "export",
            "digest",
            "report",
            "backup",
            "list-backups",
            "restore",
            "restore-latest",
            "config",
            "fins",
            "fine",
            "sync-sheets",
            "sync-status",
        ]
    ):
        # This looks like a direct task addition
        handle_direct_task(args)
    else:
        # Normal Click processing
        cli()


@cli.command(name="sync-sheets")
@click.option("--sheet-name", default="todo", help="Name of the sheet to sync from (default: todo)")
@click.option("--dry-run", is_flag=True, help="Show what would be synced without making changes")
@click.option("--purge-after-import", is_flag=True, default=True, help="Purge remote tasks after import (default: True)")
@click.option("--token-path", help="Path to Google OAuth token file (default: ~/.fin/google_token.json)")
@click.option("--sheet-id", help="Google Sheet ID (can also be set via SHEET_ID env var)")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def sync_sheets_command(sheet_name, dry_run, purge_after_import, token_path, sheet_id, verbose):
    """Sync tasks from Google Sheets."""
    try:
        # Get sheet ID from environment or parameter
        sheet_id = sheet_id or os.environ.get("SHEET_ID")
        if not sheet_id:
            click.echo("❌ Error: Sheet ID not provided. Use --sheet-id or set SHEET_ID environment variable.")
            return

        # Get token path from parameter or default
        token_path = token_path or os.path.expanduser("~/.fin/google_token.json")
        if not os.path.exists(token_path):
            click.echo(f"❌ Error: Token file not found: {token_path}")
            click.echo("   Run gcreds.py first to authenticate with Google")
            return

        if verbose:
            click.echo("🔧 Configuration:")
            click.echo(f"   • Sheet ID: {sheet_id}")
            click.echo(f"   • Sheet name: {sheet_name}")
            click.echo(f"   • Token path: {token_path}")
            click.echo(f"   • Dry run: {dry_run}")
            click.echo(f"   • Purge after import: {purge_after_import}")
            click.echo()

        # Create sheets reader
        sheets_reader = create_sheets_reader_from_token(token_path, sheet_id)

        # Create sync engine and strategy
        db_manager = _get_db_manager()
        task_manager = TaskManager(db_manager)
        sync_engine = SyncEngine(db_manager, task_manager)

        strategy = SyncStrategyFactory.create_strategy(RemoteSystemType.GOOGLE_SHEETS, sync_engine, sheets_reader=sheets_reader)

        if verbose:
            click.echo("🔄 Starting Google Sheets sync...")
            click.echo()

        # Validate sheet structure first
        validation_result = strategy.validate_sheet_structure(sheet_name)
        if not validation_result["valid"]:
            click.echo(f"❌ Sheet validation failed: {validation_result['error']}")
            if "missing_headers" in validation_result:
                click.echo(f"   Missing headers: {', '.join(validation_result['missing_headers'])}")
                click.echo(f"   Found headers: {', '.join(validation_result['found_headers'])}")
            return

        if verbose:
            click.echo("✅ Sheet structure validated successfully")
            click.echo(f"   • Total rows: {validation_result['total_rows']}")
            click.echo(f"   • Valid tasks found: {validation_result['valid_tasks_found']}")
            click.echo()

        # Perform sync
        sync_result = strategy.sync_sheet_tasks(sheet_name=sheet_name, dry_run=dry_run, purge_after_import=purge_after_import)

        if not sync_result["success"]:
            click.echo(f"❌ Sync failed: {sync_result['error']}")
            return

        # Display results
        if dry_run:
            click.echo("🔍 DRY RUN RESULTS (no changes made):")
        else:
            click.echo("✅ Sync completed successfully:")

        click.echo(f"   • Total rows in sheet: {sync_result['total_rows']}")
        click.echo(f"   • Tasks imported: {sync_result.get('tasks_imported', 0)}")
        click.echo(f"   • Tasks updated: {sync_result.get('tasks_updated', 0)}")
        click.echo(f"   • Tasks skipped: {sync_result.get('tasks_skipped', 0)}")

        if "purge_results" in sync_result:
            purge = sync_result["purge_results"]
            click.echo(f"   • Remote tasks purged: {purge.get('tasks_purged', 0)}")
            if purge.get("errors"):
                click.echo(f"   • Purge errors: {len(purge['errors'])}")

        if verbose and "errors" in sync_result and sync_result["errors"]:
            click.echo(f"   • Sync errors: {len(sync_result['errors'])}")
            for error in sync_result["errors"]:
                click.echo(f"     - {error}")

    except Exception as e:
        click.echo(f"❌ Error during sync: {str(e)}")
        if verbose:
            import traceback

            click.echo(traceback.format_exc())


@cli.command(name="sync-status")
@click.option("--source", help="Filter by remote source (e.g., google_sheets)")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def sync_status_command(source, verbose):
    """Show sync status for remote tasks."""
    try:
        db_manager = _get_db_manager()
        task_manager = TaskManager(db_manager)
        sync_engine = SyncEngine(db_manager, task_manager)

        if verbose:
            click.echo("🔍 Fetching sync status:...")
            click.echo()

        # Get sync status
        status = sync_engine.get_sync_status(remote_source=source)

        if not status:
            click.echo("📝 No remote tasks found.")
            return

        click.echo("📊 Remote Task Sync Status:")
        click.echo()

        # Display status by authority type
        for key, info in status.items():
            if key == "last_sync":
                continue

            authority, is_shadow = key.split("_", 1)
            task_type = "Shadow" if is_shadow == "True" else "Authoritative"

            click.echo(f"🔸 {authority.replace('_', ' ').title()} Authority - {task_type} Tasks:")
            click.echo(f"   • Count: {info['count']}")
            if info.get("last_sync"):
                click.echo(f"   • Last sync: {info['last_sync']}")
            click.echo()

        # Show last sync time if available
        if "last_sync" in status:
            click.echo(f"🕒 Last sync: {status['last_sync']}")

    except Exception as e:
        click.echo(f"❌ Error getting sync status: {str(e)}")
        if verbose:
            import traceback

            click.echo(traceback.format_exc())


if __name__ == "__main__":
    main()
