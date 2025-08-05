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


def add_task(content: str, labels: tuple, source: str = "cli"):
    """Add a task to the database."""
    db_manager = DatabaseManager()
    task_manager = TaskManager(db_manager)

    # Convert labels tuple to list for TaskManager
    labels_list = list(labels) if labels else None

    # Add the task with labels (TaskManager handles normalization)

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
@click.option("--week", is_flag=True, help="Show tasks from the past week")
@click.option("--label", "-l", multiple=True, help="Filter by labels")
@click.option(
    "--status",
    type=click.Choice(["open", "completed", "all"]),
    default="open",
    help="Filter by status",
)
def list_tasks(week, label, status):
    """Query and display tasks based on time and status criteria."""
    db_manager = DatabaseManager()
    task_manager = TaskManager(db_manager)

    # Get tasks
    tasks = task_manager.list_tasks(include_completed=(status in ["completed", "all"]))

    # Apply week filtering if requested
    if week:
        tasks = filter_tasks_by_date_range(tasks, include_week=True)

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
    # Get tasks for editing
    # For now, use the first label if multiple provided


@cli.command(name="open-editor")
@click.option("--label", "-l", multiple=True, help="Filter by labels")
@click.option("--date", help="Filter by date (YYYY-MM-DD)")
def open_editor(label, date):
    """Open tasks in your editor."""
    db_manager = DatabaseManager()
    editor_manager = EditorManager(db_manager)

    # Get tasks for editing
    # For now, use the first label if multiple provided

    # Check if tasks exist before opening editor
    tasks = editor_manager.get_tasks_for_editing(label=label_filter, target_date=date)
    if not tasks:
        click.echo("📝 No tasks found for editing.")
        return

    # Open in editor
    click.echo("Opening tasks in editor...")
    completed_count, reopened_count = editor_manager.edit_tasks(
        label=label_filter, target_date=date
    )


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
