"""
CLI module for FinCLI

Main entry point for all CLI commands.
"""

import sys

import click

from fincli.analytics import AnalyticsManager
from fincli.db import DatabaseManager
from fincli.editor import EditorManager
from fincli.intake import get_available_sources, import_from_source
from fincli.labels import LabelManager
from fincli.tasks import TaskManager
from fincli.utils import filter_tasks_by_date_range, format_task_for_display
from fincli.backup import DatabaseBackup
from datetime import datetime
import re


def add_task(content: str, labels: tuple, source: str = "cli"):
    """Add a task to the database."""
    db_manager = DatabaseManager()
    task_manager = TaskManager(db_manager)

    # Convert labels tuple to list for TaskManager
    labels_list = list(labels) if labels else None

    # Add the task with labels (TaskManager handles normalization)
    task_id = task_manager.add_task(content, labels_list, source)

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
    if normalized_labels:
        click.echo(f'✅ Task added: "{content}" [{", ".join(normalized_labels)}]')
    else:
        click.echo(f'✅ Task added: "{content}"')


def handle_direct_task(args):
    """Handle direct task addition: fin "task content"."""
    if not args:
        click.echo("Missing argument")
        sys.exit(1)

    # Parse arguments for labels
    task_content = []
    labels = []
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
    add_task(content, tuple(labels), "cli")


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
def cli():
    """
    FinCLI - A lightweight task tracking system

    Manage your local task database with simple commands.

    Examples:
        fin "my new task"                    # Add a task directly
        fin add-task "my new task"           # Add a task explicitly
        fin list-tasks                       # List all tasks
    """
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
    db_manager = DatabaseManager(db_path=db_path)
    # Database is automatically initialized in __init__
    click.echo("✅ Database initialized successfully!")


def _list_tasks_impl(days, label, status):
    """Implementation for listing tasks."""
    db_manager = DatabaseManager()
    task_manager = TaskManager(db_manager)

    # Get tasks (include completed tasks for status filtering)
    tasks = task_manager.list_tasks(include_completed=True)

    # Apply date filtering first
    tasks = filter_tasks_by_date_range(tasks, days=days)

    # Apply status filtering
    if status == "open":
        tasks = [task for task in tasks if task["completed_at"] is None]
    elif status in ["completed", "done"]:
        tasks = [task for task in tasks if task["completed_at"] is not None]
    # For "all", we keep all tasks (both open and completed)

    # Apply label filtering if requested
    if label:
        # Simple label filtering - could be enhanced
        filtered_tasks = []
        for task in tasks:
            if task.get("labels"):
                task_labels = [l.lower() for l in task["labels"]]
                for requested_label in label:
                    if requested_label.lower() in task_labels:
                        filtered_tasks.append(task)
                        break
        tasks = filtered_tasks

    # Display tasks
    if not tasks:
        click.echo("📝 No tasks found matching your criteria.")
        return

    for task in tasks:
        formatted_task = format_task_for_display(task)
        click.echo(formatted_task)


@cli.command(name="list-tasks")
@click.option("--days", "-d", default=1, help="Show tasks from the past N days (default: 1)")
@click.option("--label", "-l", multiple=True, help="Filter by labels")
@click.option(
    "--status", "-s",
    type=click.Choice(["open", "completed", "done", "all"]),
    default="open",
    help="Filter by status",
)
def list_tasks(days, label, status):
    """Query and display tasks based on time and status criteria."""
    _list_tasks_impl(days, label, status)


@cli.command(name="list")
@click.option("--days", "-d", default=1, help="Show tasks from the past N days (default: 1)")
@click.option("--label", "-l", multiple=True, help="Filter by labels")
@click.option(
    "--status", "-s",
    type=click.Choice(["open", "completed", "done", "all"]),
    default="open",
    help="Filter by status",
)
def list_tasks_alias(days, label, status):
    """Alias for list-tasks command."""
    _list_tasks_impl(days, label, status)


@cli.command(name="open-editor")
@click.option("--label", "-l", multiple=True, help="Filter by labels")
@click.option("--date", help="Filter by date (YYYY-MM-DD)")
@click.option("--all-tasks", is_flag=True, help="Show all tasks (including completed)")
@click.option("--dry-run", is_flag=True, help="Show what would be edited without opening editor")
def open_editor(label, date, all_tasks, dry_run):
    """Open tasks in your editor for editing completion status."""
    
    db_manager = DatabaseManager()
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
        original_open = [t for t in original_tasks if not t.get("completed_at")]
        
        completed_count, reopened_count, new_tasks_count, deleted_count = editor_manager.edit_tasks(
            label=label_filter, target_date=date, all_tasks=all_tasks
        )
        
        # Get the state after editing for detailed comparison
        updated_tasks = editor_manager.get_tasks_for_editing(label=label_filter, target_date=date, all_tasks=all_tasks)
        updated_completed = [t for t in updated_tasks if t.get("completed_at")]
        updated_open = [t for t in updated_tasks if not t.get("completed_at")]
        
        changes_made = completed_count > 0 or reopened_count > 0 or new_tasks_count > 0 or deleted_count > 0
        
        if changes_made:
            click.echo("\n📊 Summary of Changes:")
            click.echo("=" * 40)
            
            # Show completed tasks
            if completed_count > 0:
                click.echo(f"✅ Completed ({completed_count}):")
                original_completed_ids = {t['id'] for t in original_completed}
                newly_completed = [t for t in updated_completed if t['id'] not in original_completed_ids]
                for task in newly_completed:
                    click.echo(f"  • {task['content']}")
                click.echo()
            
            # Show reopened tasks
            if reopened_count > 0:
                click.echo(f"🔄 Reopened ({reopened_count}):")
                newly_reopened = [t for t in updated_open if t['id'] in original_completed_ids]
                for task in newly_reopened:
                    click.echo(f"  • {task['content']}")
                click.echo()
            
            # Show new tasks
            if new_tasks_count > 0:
                click.echo(f"📝 Added ({new_tasks_count}):")
                # Get the most recent tasks that weren't in the original list
                all_tasks = editor_manager.task_manager.list_tasks(include_completed=True)
                original_ids = {t['id'] for t in original_tasks}
                new_tasks = [t for t in all_tasks if t['id'] not in original_ids]
                # Sort by creation time (newest first) and take the most recent ones
                new_tasks.sort(key=lambda x: x['created_at'], reverse=True)
                for task in new_tasks[:new_tasks_count]:
                    labels_str = f" [{', '.join(task['labels'])}]" if task['labels'] else ""
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
    """
    import click
    
    # Create a standalone Click command
    @click.command(context_settings=dict(help_option_names=["-h", "--help"]))
    @click.option("--label", "-l", multiple=True, help="Filter by labels")
    @click.option("--date", help="Filter by date (YYYY-MM-DD)")
    @click.option("--days", "-d", default=1, help="Show tasks from the past N days (default: 1)")
    @click.option("--dry-run", is_flag=True, help="Show what would be edited without opening editor")
    @click.option(
        "--status", "-s",
        type=click.Choice(["open", "completed", "done", "all"]),
        default="open",
        help="Filter by status (default: open)",
    )
    def fine_cli(label, date, days, dry_run, status):
        """Edit tasks in your editor (alias for fin open-editor)."""
        # Call the original open_editor function directly
        db_manager = DatabaseManager()
        editor_manager = EditorManager(db_manager)

        # Get tasks for editing (without opening editor)
        label_filter = label[0] if label else None
        
        # If no specific date is provided, use days filtering
        if not date:
            # Get all tasks and apply days filtering
            all_tasks = editor_manager.task_manager.list_tasks(include_completed=True)
            from fincli.utils import filter_tasks_by_date_range
            tasks = filter_tasks_by_date_range(all_tasks, days=days)
            
            # Apply status filtering
            if status == "open":
                tasks = [task for task in tasks if task["completed_at"] is None]
            elif status in ["completed", "done"]:
                tasks = [task for task in tasks if task["completed_at"] is not None]
            # For "all", we keep all tasks (both open and completed)
            
            # Convert back to the format expected by editor_manager
            task_ids = [task['id'] for task in tasks]
            tasks = editor_manager.get_tasks_for_editing(all_tasks=True)
            # Filter to only include tasks from our date range and status
            tasks = [task for task in tasks if task['id'] in task_ids]
        else:
            # For date-based filtering, we need to handle status filtering differently
            # since editor_manager.get_tasks_for_editing doesn't support status filtering
            all_tasks = editor_manager.task_manager.list_tasks(include_completed=True)
            from fincli.utils import filter_tasks_by_date_range
            
            # Apply date filtering
            tasks = filter_tasks_by_date_range(all_tasks, days=0)  # Use 0 for specific date
            
            # Apply status filtering
            if status == "open":
                tasks = [task for task in tasks if task["completed_at"] is None]
            elif status in ["completed", "done"]:
                tasks = [task for task in tasks if task["completed_at"] is not None]
            # For "all", we keep all tasks (both open and completed)
            
            # Convert to editor format
            task_ids = [task['id'] for task in tasks]
            tasks = editor_manager.get_tasks_for_editing(all_tasks=True)
            tasks = [task for task in tasks if task['id'] in task_ids]
        
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
        try:
            # Get the state before editing for comparison
            original_tasks = tasks.copy()
            original_completed = [t for t in original_tasks if t.get("completed_at")]
            original_open = [t for t in original_tasks if not t.get("completed_at")]
            
            completed_count, reopened_count, new_tasks_count, deleted_count = editor_manager.edit_tasks(
                label=label_filter, target_date=date, all_tasks=True
            )
            
            # Get the state after editing for detailed comparison
            updated_tasks = editor_manager.get_tasks_for_editing(label=label_filter, target_date=date, all_tasks=True)
            updated_completed = [t for t in updated_tasks if t.get("completed_at")]
            updated_open = [t for t in updated_tasks if not t.get("completed_at")]
            
            changes_made = completed_count > 0 or reopened_count > 0 or new_tasks_count > 0 or deleted_count > 0
            
            if changes_made:
                click.echo("\n📊 Summary of Changes:")
                click.echo("=" * 40)
                
                # Show completed tasks
                if completed_count > 0:
                    click.echo(f"✅ Completed ({completed_count}):")
                    original_completed_ids = {t['id'] for t in original_completed}
                    newly_completed = [t for t in updated_completed if t['id'] not in original_completed_ids]
                    for task in newly_completed:
                        click.echo(f"  • {task['content']}")
                    click.echo()
                
                # Show reopened tasks
                if reopened_count > 0:
                    click.echo(f"🔄 Reopened ({reopened_count}):")
                    newly_reopened = [t for t in updated_open if t['id'] in original_completed_ids]
                    for task in newly_reopened:
                        click.echo(f"  • {task['content']}")
                    click.echo()
                
                # Show new tasks
                if new_tasks_count > 0:
                    click.echo(f"📝 Added ({new_tasks_count}):")
                    # Get the most recent tasks that weren't in the original list
                    all_tasks = editor_manager.task_manager.list_tasks(include_completed=True)
                    original_ids = {t['id'] for t in original_tasks}
                    new_tasks = [t for t in all_tasks if t['id'] not in original_ids]
                    # Sort by creation time (newest first) and take the most recent ones
                    new_tasks.sort(key=lambda x: x['created_at'], reverse=True)
                    for task in new_tasks[:new_tasks_count]:
                        labels_str = f" [{', '.join(task['labels'])}]" if task['labels'] else ""
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
    @click.option("--days", "-d", default=7, help="Show tasks from the past N days (default: 7)")
    @click.option("--label", "-l", multiple=True, help="Filter by labels")
    @click.option("--today", is_flag=True, help="Show only today's tasks (overrides default days behavior)")
    @click.option(
        "--status", "-s",
        type=click.Choice(["open", "completed", "done", "all"]),
        default="completed",
        help="Filter by status (default: completed)",
    )
    def fins_cli(content, days, label, today, status):
        """Query and display completed tasks, or add completed tasks."""
        # If content is provided, add it as a completed task
        if content:
            task_content = " ".join(content)
            db_manager = DatabaseManager()
            task_manager = TaskManager(db_manager)
            
            # Add the task as completed
            task_id = task_manager.add_task(task_content, labels=label, source="fins")
            
            # Mark it as completed immediately
            task_manager.update_task_completion(task_id, True)
            
            click.echo(f"✅ Task added and marked as completed: {task_content}")
            return
        
        # Otherwise, show tasks (existing behavior)
        db_manager = DatabaseManager()
        task_manager = TaskManager(db_manager)

        # Get tasks (include completed tasks for status filtering)
        tasks = task_manager.list_tasks(include_completed=True)

        # Apply date filtering first
        if today:
            # Override to show only today's tasks
            tasks = filter_tasks_by_date_range(tasks, days=0)
        else:
            # Default: show tasks from past N days
            tasks = filter_tasks_by_date_range(tasks, days=days)

        # Apply status filtering
        if status == "open":
            tasks = [task for task in tasks if task["completed_at"] is None]
        elif status in ["completed", "done"]:
            tasks = [task for task in tasks if task["completed_at"] is not None]
        # For "all", we keep all tasks (both open and completed)

        # Apply label filtering if requested
        if label:
            # Simple label filtering - could be enhanced
            filtered_tasks = []
            for task in tasks:
                if task.get("labels"):
                    task_labels = [l.lower() for l in task["labels"]]
                    for requested_label in label:
                        if requested_label.lower() in task_labels:
                            filtered_tasks.append(task)
                            break
            tasks = filtered_tasks

        # Display tasks
        if not tasks:
            click.echo("📝 No tasks found matching your criteria.")
            return

        for task in tasks:
            formatted_task = format_task_for_display(task)
            click.echo(formatted_task)
    
    # Run the fins CLI
    fins_cli()


@cli.command(name="list-labels")
def list_labels():
    """List all known labels."""
    db_manager = DatabaseManager()
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
    db_manager = DatabaseManager()
    backup_manager = DatabaseBackup(db_manager.db_path)
    
    backup_id = backup_manager.create_backup(description or "Manual backup")
    
    if backup_id > 0:
        click.echo(f"✅ Backup created: backup_{backup_id:03d}")
    else:
        click.echo("❌ No database found to backup")


@cli.command(name="list-backups")
def list_backups():
    """List all available backups."""
    db_manager = DatabaseManager()
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
    db_manager = DatabaseManager()
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
    db_manager = DatabaseManager()
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
@click.option("--format", "-f", type=click.Choice(["csv", "json", "txt"]), default="csv", help="Export format")
@click.option("--include-completed", is_flag=True, default=True, help="Include completed tasks (default: True)")
def export_tasks(file_path, format, include_completed):
    """Export all tasks to a flat file."""
    db_manager = DatabaseManager()
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
    
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['ID', 'Content', 'Status', 'Created', 'Completed', 'Labels', 'Source']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for task in tasks:
            status = "completed" if task["completed_at"] else "open"
            labels = ",".join(task.get("labels", [])) if task.get("labels") else ""
            
            writer.writerow({
                'ID': task["id"],
                'Content': task["content"],
                'Status': status,
                'Created': task["created_at"],
                'Completed': task["completed_at"] or "",
                'Labels': labels,
                'Source': task.get("source", "cli")
            })


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
            "source": task.get("source", "cli")
        }
        export_data.append(export_task)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)


def _export_txt(tasks, file_path):
    """Export tasks to plain text format using editor format."""
    from fincli.editor import EditorManager
    
    db_manager = DatabaseManager()
    editor_manager = EditorManager(db_manager)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"# FinCLI Task Export - {len(tasks)} tasks\n")
        f.write(f"# Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for task in tasks:
            # Use the same formatting as the editor
            task_line = editor_manager._format_task_with_reference(task)
            f.write(f"{task_line}\n")


@cli.command(name="import")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--format", "-f", type=click.Choice(["csv", "json", "txt"]), help="Import format (auto-detected if not specified)")
@click.option("--label", "-l", multiple=True, help="Add labels to imported tasks")
@click.option("--clear-existing", is_flag=True, help="Clear existing tasks before import")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt (alias for --force)")
def import_tasks_from_file(file_path, format, label, clear_existing, force, yes):
    """Import tasks from a flat file."""
    db_manager = DatabaseManager()
    task_manager = TaskManager(db_manager)
    
    # Auto-detect format if not specified
    if not format:
        if file_path.endswith('.csv'):
            format = 'csv'
        elif file_path.endswith('.json'):
            format = 'json'
        elif file_path.endswith('.txt'):
            format = 'txt'
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
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row.get('Content', '').strip():
                        task_count += 1
                        if row.get('Status') == 'completed':
                            completed_count += 1
        
        elif format == "json":
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for task_data in data:
                    if task_data.get('content', '').strip():
                        task_count += 1
                        if task_data.get('status') == 'completed':
                            completed_count += 1
        
        elif format == "txt":
            from fincli.editor import EditorManager
            db_manager = DatabaseManager()
            editor_manager = EditorManager(db_manager)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    task_info = editor_manager.parse_task_line(line)
                    if task_info and task_info["content"].strip():
                        task_count += 1
                        if task_info["is_completed"]:
                            completed_count += 1
        
        preview_lines.append(f"📊 File contains: {task_count} tasks ({completed_count} completed)")
        
        # Show current database stats
        db_manager = DatabaseManager()
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
    
    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            content = row.get('Content', '').strip()
            if not content:
                continue
            
            # Parse labels
            labels = []
            if row.get('Labels'):
                labels.extend([label.strip() for label in row['Labels'].split(',') if label.strip()])
            
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
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for task_data in data:
        content = task_data.get('content', '').strip()
        if not content:
            continue
        
        # Parse labels
        labels = task_data.get('labels', [])
        labels.extend(additional_labels)
        
        # Add task
        task_id = task_manager.add_task(content, labels, source="json-import")
        imported_count += 1
        
        # Mark as completed if it was completed in the export
        if task_data.get('status') == 'completed' and task_data.get('completed_at'):
            task_manager.update_task_completion(task_id, True)
    
    return imported_count


def _import_txt(task_manager, file_path, additional_labels):
    """Import tasks from plain text format using editor parsing."""
    from fincli.editor import EditorManager
    
    db_manager = DatabaseManager()
    editor_manager = EditorManager(db_manager)
    
    imported_count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
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
    db_manager = DatabaseManager()
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
    db_manager = DatabaseManager()
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


def main():
    """Main entry point that handles direct task addition."""
    args = sys.argv[1:]

    # If no arguments provided, default to list behavior
    if not args:
        db_manager = DatabaseManager()
        task_manager = TaskManager(db_manager)
        
        # Get tasks with default filtering (today and yesterday, open tasks)
        tasks = task_manager.list_tasks(include_completed=True)
        tasks = filter_tasks_by_date_range(tasks, days=1)
        tasks = [task for task in tasks if task["completed_at"] is None]
        
        if not tasks:
            click.echo("📝 No open tasks found for today and yesterday.")
            click.echo("💡 Try adding a task: fin 'your task here'")
            click.echo("💡 Or see all commands: fin --help")
            return
        else:
            # Display tasks
            for task in tasks:
                formatted_task = format_task_for_display(task)
                click.echo(formatted_task)
            return

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
            "list-labels",
            "import",
            "export",
            "digest",
            "report",
            "backup",
            "list-backups",
            "restore",
            "restore-latest",
            "fins",
            "--help",
            "-h",
            "--version",
            "-v",
        ]
    ):
        # This looks like a direct task addition
        handle_direct_task(args)
    else:
        # Normal Click processing
        cli()


if __name__ == "__main__":
    main()
