"""
Legacy CLI entry point for backward compatibility
"""
import click
from fin.database.manager import DatabaseManager


@click.command()
@click.argument('content', required=True)
@click.option('--label', '-l', multiple=True, help='Labels for the task (can be specified multiple times)')
@click.option('--source', '-s', default='cli', help='Source of the task (default: cli)')
def legacy_main(content: str, label: tuple, source: str):
    """
    Fin - A lightweight task tracking system
    
    Add a new task to your local task database.
    
    Examples:
        fin "write up product notes"
        fin "review pull request" --label work,urgent
        fin "buy groceries" -l personal -l shopping
    """
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Convert tuple of labels to list
        labels = list(label) if label else None
        
        # Add task to database
        task_id = db_manager.add_task(content, labels, source)
        
        # Get the task to display normalized labels
        task = db_manager.get_task(task_id)
        
        # Format labels for display
        labels_display = ""
        if task['labels']:
            labels_display = f" [{', '.join(task['labels'])}]"
        
        # Print success message
        click.echo(f"✅ Task added: \"{content}\"{labels_display}")
        
    except Exception as e:
        click.echo(f"❌ Error adding task: {str(e)}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    legacy_main() 