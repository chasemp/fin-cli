"""
CLI module for FinCLI

Main entry point for all CLI commands.
"""
import click
from .db import DatabaseManager
from .tasks import TaskManager
from .labels import LabelManager
from .editor import EditorManager
from .utils import format_task_for_display, filter_tasks_by_date_range
from .intake import import_from_source, get_available_sources


@click.group()
def cli():
    """
    FinCLI - A lightweight task tracking system
    
    Manage your local task database with simple commands.
    """
    pass


@cli.command()
@click.option('--db-path', help='Custom database path (default: ~/fin/tasks.db)')
def init(db_path: str):
    """
    Initialize the Fin task database.
    
    Creates the database file and sets up the schema if it doesn't exist.
    This command is optional - the database is automatically created when needed.
    
    Examples:
        fin init
        fin init --db-path ~/my-tasks.db
    """
    try:
        # Initialize database
        db_manager = DatabaseManager(db_path)
        
        # Test the connection
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks")
            task_count = cursor.fetchone()[0]
        
        click.echo(f"✅ Fin database initialized successfully!")
        click.echo(f"📁 Database location: {db_manager.db_path}")
        click.echo(f"📊 Current tasks: {task_count}")
        click.echo(f"🚀 Ready to use! Try: fin add \"your first task\"")
        
    except Exception as e:
        click.echo(f"❌ Error initializing database: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('content', required=True)
@click.option('--label', '-l', multiple=True, help='Labels for the task (can be specified multiple times)')
@click.option('--source', '-s', default='cli', help='Source of the task (default: cli)')
def add_task(content: str, label: tuple, source: str):
    """
    Add a new task to your local task database.
    
    Examples:
        fin add "write up product notes"
        fin add "review pull request" --label work,urgent
        fin add "buy groceries" -l personal -l shopping
    """
    try:
        # Initialize managers
        db_manager = DatabaseManager()
        task_manager = TaskManager(db_manager)
        
        # Convert tuple of labels to list
        labels = list(label) if label else None
        
        # Add task to database
        task_id = task_manager.add_task(content, labels, source)
        
        # Get the task to display normalized labels
        task = task_manager.get_task(task_id)
        
        # Format labels for display
        labels_display = ""
        if task['labels']:
            labels_display = f" [{', '.join(task['labels'])}]"
        
        # Print success message
        click.echo(f"✅ Task added: \"{content}\"{labels_display}")
        
    except Exception as e:
        click.echo(f"❌ Error adding task: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--week', '-w', is_flag=True, help='Include completed tasks from the past 7 days')
@click.option('--label', '-l', help='Filter tasks by label (case-insensitive, partial match)')
def list_tasks(week: bool, label: str):
    """
    Query and display tasks based on time and status.
    
    By default, shows:
    - Open tasks from today
    - Completed tasks from yesterday
    
    With --week flag, also shows completed tasks from the past 7 days.
    With --label, filters tasks to only those containing the specified label.
    """
    try:
        # Initialize managers
        db_manager = DatabaseManager()
        task_manager = TaskManager(db_manager)
        label_manager = LabelManager(db_manager)
        
        # Query tasks
        if label:
            # Filter by label
            tasks = label_manager.filter_tasks_by_label(label, include_completed=True)
            formatted_tasks = [format_task_for_display(task) for task in tasks]
        else:
            # Use default time-based filtering
            all_tasks = task_manager.list_tasks(include_completed=True)
            filtered_tasks = filter_tasks_by_date_range(all_tasks, include_week=week)
            formatted_tasks = [format_task_for_display(task) for task in filtered_tasks]
        
        # Display results
        if formatted_tasks:
            for task_line in formatted_tasks:
                click.echo(task_line)
        else:
            if label:
                click.echo(f"🎉 No tasks found with label '{label}'")
            else:
                click.echo("🎉 Nothing pending today. You're all caught up!")
            
    except Exception as e:
        click.echo(f"❌ Error querying tasks: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--label', '-l', help='Only show tasks with a specific label')
@click.option('--date', '-d', help='Only show tasks from a specific date (YYYY-MM-DD)')
def open_editor(label: str, date: str):
    """
    Open tasks in your editor for review and editing.
    
    By default, shows:
    - Open tasks from today
    - Completed tasks from yesterday
    
    You can toggle task completion by changing [ ] to [x] or vice versa.
    """
    try:
        # Initialize managers
        db_manager = DatabaseManager()
        editor_manager = EditorManager(db_manager)
        
        # Get tasks for editing
        tasks = editor_manager.get_tasks_for_editing(label, date)
        
        if not tasks:
            click.echo("🎉 No tasks found matching your criteria!")
            return
        
        # Get editor command
        from .utils import get_editor
        editor_cmd = get_editor()
        
        # Open file in editor
        click.echo(f"📝 Opening {len(tasks)} tasks in {editor_cmd}...")
        click.echo("💡 Toggle checkboxes [ ] ↔ [x] to mark tasks complete/incomplete")
        
        # Edit tasks
        completed_count, reopened_count = editor_manager.edit_tasks(label, date)
        
        # Show summary
        total_updated = completed_count + reopened_count
        if total_updated > 0:
            click.echo(f"✅ Updated {total_updated} tasks ({completed_count} completed, {reopened_count} reopened)")
        else:
            click.echo("ℹ️  No changes detected")
            
    except Exception as e:
        click.echo(f"❌ Error editing tasks: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
def list_labels():
    """
    List all known labels from existing tasks.
    
    Shows all unique labels that have been used across all tasks.
    """
    try:
        # Initialize managers
        db_manager = DatabaseManager()
        label_manager = LabelManager(db_manager)
        
        # Get all labels
        labels = label_manager.get_all_labels()
        
        if labels:
            click.echo("Known labels:")
            for label in labels:
                click.echo(f"- {label}")
        else:
            click.echo("No labels found in any tasks.")
            
    except Exception as e:
        click.echo(f"❌ Error listing labels: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--source', required=True, help='Source to import from')
@click.option('--file', help='Path to import file (optional, uses defaults)')
@click.option('--delete-after-import', is_flag=True, help='Delete source file after successful import')
@click.option('--dry-run', is_flag=True, help='Show what would be imported without actually importing')
def import_tasks(source: str, file: str, delete_after_import: bool, dry_run: bool):
    """
    Import tasks from external sources.
    
    Available sources: csv, json, text, sheets, excel
    
    Examples:
        fin-import --source csv
        fin-import --source json --file /path/to/tasks.json
        fin-import --source text --delete-after-import
    """
    try:
        # Check if source is available
        available_sources = get_available_sources()
        if source not in available_sources:
            click.echo(f"❌ Unknown source: {source}")
            click.echo(f"Available sources: {', '.join(available_sources)}")
            raise click.Abort()
        
        # Prepare import arguments
        import_args = {}
        if file:
            import_args['file_path'] = file
        if delete_after_import:
            import_args['delete_after_import'] = True
        if dry_run:
            import_args['dry_run'] = True
        
        # Import tasks
        result = import_from_source(source, **import_args)
        
        # Display results
        if result['success']:
            click.echo(f"✅ Imported {result['imported']} tasks from {source}")
            if result['skipped'] > 0:
                click.echo(f"⚠️  Skipped {result['skipped']} items")
            if result.get('errors'):
                click.echo(f"⚠️  {len(result['errors'])} errors occurred")
                for error in result['errors'][:5]:  # Show first 5 errors
                    click.echo(f"   {error}")
        else:
            click.echo(f"❌ Import failed: {result['error']}")
            if result.get('note'):
                click.echo(f"💡 {result['note']}")
            raise click.Abort()
            
    except Exception as e:
        click.echo(f"❌ Error importing tasks: {str(e)}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli() 