"""
Main CLI entry point for Fin task tracking system
"""
import click
from fin.database.manager import DatabaseManager
from fin.cli.commands import fins, fine, list_labels


def add_task(content: str, label: tuple, source: str):
    """Add a new task to the database."""
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


@click.group()
def main():
    """
    Fin - A lightweight task tracking system
    
    Manage your local task database with simple commands.
    """
    pass


@main.command()
@click.argument('content', required=True)
@click.option('--label', '-l', multiple=True, help='Labels for the task (can be specified multiple times)')
@click.option('--source', '-s', default='cli', help='Source of the task (default: cli)')
def add(content: str, label: tuple, source: str):
    """
    Add a new task to your local task database.
    
    Examples:
        fin add "write up product notes"
        fin add "review pull request" --label work,urgent
        fin add "buy groceries" -l personal -l shopping
    """
    add_task(content, label, source)


# Add fins command
main.add_command(fins)

# Add fine command
main.add_command(fine)

# Add list-labels command
main.add_command(list_labels)





if __name__ == '__main__':
    main() 