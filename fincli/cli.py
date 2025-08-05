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
    db_manager.initialize()
    click.echo("✅ Database initialized successfully!")


@cli.command(name="list-tasks")
@click.option("--days", "-d", default=1, help="Show tasks from the past N days (default: 1)")
@click.option("--label", "-l", multiple=True, help="Filter by labels")
@click.option(
    "--status", "-s",
    type=click.Choice(["open", "completed", "all"]),
    default="open",
    help="Filter by status",
)
def list_tasks(days, label, status):
    """Query and display tasks based on time and status criteria."""
    db_manager = DatabaseManager()
    task_manager = TaskManager(db_manager)

    # Get tasks (include completed tasks if we need them for status filtering)
    tasks = task_manager.list_tasks(include_completed=True)

    # Apply date filtering first
    tasks = filter_tasks_by_date_range(tasks, days=days)

    # Apply status filtering
    if status == "open":
        tasks = [task for task in tasks if task["completed_at"] is None]
    elif status == "completed":
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
    @click.command()
    @click.option("--label", "-l", multiple=True, help="Filter by labels")
    @click.option("--date", help="Filter by date (YYYY-MM-DD)")
    @click.option("--days", "-d", default=1, help="Show tasks from the past N days (default: 1)")
    @click.option("--dry-run", is_flag=True, help="Show what would be edited without opening editor")
    @click.option(
        "--status", "-s",
        type=click.Choice(["open", "completed", "all"]),
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
            elif status == "completed":
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
            elif status == "completed":
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
    @click.command()
    @click.option("--days", "-d", default=7, help="Show tasks from the past N days (default: 7)")
    @click.option("--label", "-l", multiple=True, help="Filter by labels")
    @click.option("--today", is_flag=True, help="Show only today's tasks (overrides default days behavior)")
    @click.option(
        "--status", "-s",
        type=click.Choice(["open", "completed", "all"]),
        default="completed",
        help="Filter by status (default: completed)",
    )
    def fins_cli(days, label, today, status):
        """Query and display completed tasks (defaults to completed tasks from past 7 days)."""
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
        elif status == "completed":
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
def restore_backup(backup_id, force):
    """Restore database from a backup."""
    db_manager = DatabaseManager()
    backup_manager = DatabaseBackup(db_manager.db_path)
    
    if not force:
        click.echo(f"⚠️  This will overwrite your current database with backup_{backup_id:03d}")
        click.echo("   This action cannot be undone!")
        if not click.confirm("Do you want to continue?"):
            click.echo("Restore cancelled")
            return
    
    if backup_manager.rollback(backup_id):
        click.echo(f"✅ Successfully restored from backup_{backup_id:03d}")
    else:
        click.echo(f"❌ Failed to restore from backup_{backup_id:03d}")


@cli.command(name="restore-latest")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def restore_latest_backup(force):
    """Restore database from the latest backup."""
    db_manager = DatabaseManager()
    backup_manager = DatabaseBackup(db_manager.db_path)
    
    latest_id = backup_manager.get_latest_backup_id()
    if latest_id is None:
        click.echo("❌ No backups found")
        return
    
    if not force:
        click.echo(f"⚠️  This will overwrite your current database with backup_{latest_id:03d}")
        click.echo("   This action cannot be undone!")
        if not click.confirm("Do you want to continue?"):
            click.echo("Restore cancelled")
            return
    
    if backup_manager.restore_latest():
        click.echo(f"✅ Successfully restored from backup_{latest_id:03d}")
    else:
        click.echo(f"❌ Failed to restore from backup_{latest_id:03d}")


@cli.command(name="import")
@click.argument("source")
@click.argument("file_path")
@click.option("--label", "-l", multiple=True, help="Add labels to imported tasks")
@click.option("--remove-rows", is_flag=True, help="Remove processed rows from source")
def import_tasks(source, file_path, label, remove_rows):
    """Import tasks from external sources."""
    available_sources = get_available_sources()

    if source not in available_sources:
        click.echo(f"❌ Error: Unknown source '{source}'")
        click.echo(f"Available sources: {', '.join(available_sources)}")
        raise click.Abort()

    try:
        imported_count = import_from_source(source, file_path, label, remove_rows)
        click.echo(f"✅ Successfully imported {imported_count} tasks from {source}")
    except Exception as e:
        click.echo(f"❌ Error importing from {source}: {e}")
        raise click.Abort()


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
            "open-editor",
            "list-labels",
            "import",
            "digest",
            "report",
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
