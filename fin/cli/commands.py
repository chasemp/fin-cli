"""
CLI commands for Fin task tracking system
"""
import click
import tempfile
import os
import subprocess
import re
from datetime import datetime, date, timedelta
from fin.database.manager import DatabaseManager


def format_task_for_display(task):
    """
    Format a task for display in syslog-like Markdown format.
    
    Args:
        task: Task dictionary from database
        
    Returns:
        Formatted string: [ ] 2025-07-30 09:15  Task content  #label1,label2
    """
    # Determine status
    status = "[x]" if task['completed_at'] else "[ ]"
    
    # Format timestamp
    if task['completed_at']:
        # Use completed_at for completed tasks
        timestamp = datetime.fromisoformat(task['completed_at'].replace('Z', '+00:00'))
    else:
        # Use created_at for open tasks
        timestamp = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00'))
    
    formatted_time = timestamp.strftime("%Y-%m-%d %H:%M")
    
    # Format labels as hashtags
    labels_display = ""
    if task['labels']:
        hashtags = [f"#{label}" for label in task['labels']]
        labels_display = f"  {','.join(hashtags)}"
    
    return f"{status} {formatted_time}  {task['content']}{labels_display}"


def get_date_range(include_week=False):
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


def query_tasks(db_manager, include_week=False):
    """
    Query tasks based on time and status criteria.
    
    Args:
        db_manager: Database manager instance
        include_week: If True, include completed tasks from past 7 days
        
    Returns:
        List of formatted task strings
    """
    today, yesterday, week_ago = get_date_range(include_week)
    
    # Get all tasks
    all_tasks = db_manager.list_tasks(include_completed=True)
    
    # Filter tasks based on criteria
    filtered_tasks = []
    
    for task in all_tasks:
        task_date = None
        
        # Determine the relevant date for this task
        if task['completed_at']:
            # For completed tasks, use completed_at date
            completed_dt = datetime.fromisoformat(task['completed_at'].replace('Z', '+00:00'))
            task_date = completed_dt.date()
        else:
            # For open tasks, use created_at date
            created_dt = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00'))
            task_date = created_dt.date()
        
        # Apply filtering criteria
        if task['completed_at'] is None:
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
    filtered_tasks.sort(key=lambda x: x['created_at'])
    
    return [format_task_for_display(task) for task in filtered_tasks]


def get_editor():
    """
    Get the editor command to use.
    
    Returns:
        Editor command string
    """
    editor = os.environ.get('EDITOR')
    if editor:
        return editor
    
    # Fallback editors
    for fallback in ['nano', 'vim', 'code']:
        if subprocess.run(['which', fallback], capture_output=True).returncode == 0:
            return fallback
    
    # Final fallback
    return 'nano'


def parse_task_line(line):
    """
    Parse a task line to extract task ID and completion status.
    
    Args:
        line: Task line from the file
        
    Returns:
        Dictionary with task info or None if not a valid task line
    """
    # Match task line pattern: [ ] or [x] followed by timestamp and content
    pattern = r'^(\[ \]|\[x\]) (\d{4}-\d{2}-\d{2} \d{2}:\d{2})  (.+?)(  #.+)?$'
    match = re.match(pattern, line.strip())
    
    if not match:
        return None
    
    status = match.group(1)
    timestamp = match.group(2)
    content = match.group(3)
    labels_part = match.group(4) or ""
    
    # Extract labels from hashtags
    labels = []
    if labels_part:
        hashtags = re.findall(r'#([^,#]+)', labels_part)
        labels = [tag.strip() for tag in hashtags]
    
    is_completed = status == "[x]"
    
    return {
        'status': status,
        'timestamp': timestamp,
        'content': content,
        'labels': labels,
        'is_completed': is_completed
    }


def find_matching_task(task_info, db_manager):
    """
    Find a matching task in the database based on content, timestamp, and labels.
    
    Args:
        task_info: Parsed task information
        db_manager: Database manager instance
        
    Returns:
        Task ID if found, None otherwise
    """
    all_tasks = db_manager.list_tasks(include_completed=True)
    
    for task in all_tasks:
        # Check if content matches
        if task['content'] != task_info['content']:
            continue
        
        # Check if labels match
        task_labels = set(task['labels']) if task['labels'] else set()
        info_labels = set(task_info['labels'])
        if task_labels != info_labels:
            continue
        
        # Check if timestamp matches (allowing for slight differences)
        task_timestamp = None
        if task['completed_at']:
            task_timestamp = datetime.fromisoformat(task['completed_at'].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M")
        else:
            task_timestamp = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M")
        
        if task_timestamp == task_info['timestamp']:
            return task['id']
    
    return None


def update_task_completion(task_id, is_completed, db_manager):
    """
    Update task completion status in the database.
    
    Args:
        task_id: Task ID to update
        is_completed: Whether the task should be marked as completed
        db_manager: Database manager instance
        
    Returns:
        True if updated, False if no change needed
    """
    task = db_manager.get_task(task_id)
    if not task:
        return False
    
    current_completed = task['completed_at'] is not None
    if current_completed == is_completed:
        return False  # No change needed
    
    if is_completed:
        # Mark as completed
        with db_manager.db_path.parent / db_manager.db_path.name.replace('.db', '_temp.db') as temp_db:
            import sqlite3
            with sqlite3.connect(db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tasks SET completed_at = CURRENT_TIMESTAMP WHERE id = ?", 
                    (task_id,)
                )
                conn.commit()
    else:
        # Mark as reopened
        with db_manager.db_path.parent / db_manager.db_path.name.replace('.db', '_temp.db') as temp_db:
            import sqlite3
            with sqlite3.connect(db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tasks SET completed_at = NULL WHERE id = ?", 
                    (task_id,)
                )
                conn.commit()
    
    return True


def filter_tasks_by_criteria(db_manager, label=None, target_date=None):
    """
    Filter tasks based on label and date criteria.
    
    Args:
        db_manager: Database manager instance
        label: Optional label to filter by
        target_date: Optional date to filter by (YYYY-MM-DD format)
        
    Returns:
        List of task dictionaries
    """
    all_tasks = db_manager.list_tasks(include_completed=True)
    filtered_tasks = []
    
    for task in all_tasks:
        # Filter by label if specified
        if label:
            task_labels = set(task['labels']) if task['labels'] else set()
            if label.lower() not in {l.lower() for l in task_labels}:
                continue
        
        # Filter by date if specified
        if target_date:
            try:
                target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
                task_date = None
                
                if task['completed_at']:
                    completed_dt = datetime.fromisoformat(task['completed_at'].replace('Z', '+00:00'))
                    task_date = completed_dt.date()
                else:
                    created_dt = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00'))
                    task_date = created_dt.date()
                
                if task_date != target_dt:
                    continue
            except ValueError:
                # Invalid date format, skip this filter
                pass
        
        filtered_tasks.append(task)
    
    # Sort by created_at ascending
    filtered_tasks.sort(key=lambda x: x['created_at'])
    
    return filtered_tasks


@click.command()
@click.option('--week', '-w', is_flag=True, help='Include completed tasks from the past 7 days')
@click.option('--label', '-l', help='Filter tasks by label (case-insensitive, partial match)')
def fins(week, label):
    """
    Query and display tasks based on time and status.
    
    By default, shows:
    - Open tasks from today
    - Completed tasks from yesterday
    
    With --week flag, also shows completed tasks from the past 7 days.
    With --label, filters tasks to only those containing the specified label.
    """
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Query tasks
        if label:
            # Filter by label
            tasks = db_manager.filter_tasks_by_label(label, include_completed=True)
            formatted_tasks = [format_task_for_display(task) for task in tasks]
        else:
            # Use default time-based filtering
            formatted_tasks = query_tasks(db_manager, include_week=week)
        
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


@click.command()
def list_labels():
    """
    List all known labels from existing tasks.
    
    Shows all unique labels that have been used across all tasks.
    """
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get all labels
        labels = db_manager.get_all_labels()
        
        if labels:
            click.echo("Known labels:")
            for label in labels:
                click.echo(f"- {label}")
        else:
            click.echo("No labels found in any tasks.")
            
    except Exception as e:
        click.echo(f"❌ Error listing labels: {str(e)}", err=True)
        raise click.Abort()


@click.command()
@click.option('--label', '-l', help='Only show tasks with a specific label')
@click.option('--date', '-d', help='Only show tasks from a specific date (YYYY-MM-DD)')
def fine(label, date):
    """
    Open tasks in your editor for review and editing.
    
    By default, shows:
    - Open tasks from today
    - Completed tasks from yesterday
    
    You can toggle task completion by changing [ ] to [x] or vice versa.
    """
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get tasks based on criteria
        if label or date:
            # Use custom filtering
            tasks = filter_tasks_by_criteria(db_manager, label=label, target_date=date)
            formatted_tasks = [format_task_for_display(task) for task in tasks]
        else:
            # Use default filtering (today's open + yesterday's completed)
            formatted_tasks = query_tasks(db_manager, include_week=False)
        
        if not formatted_tasks:
            click.echo("🎉 No tasks found matching your criteria!")
            return
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            # Write header
            temp_file.write("# Fin Tasks - Edit and save to update completion status\n")
            temp_file.write("# Only checkbox changes ([ ] ↔ [x]) are tracked\n\n")
            
            # Write tasks
            for task_line in formatted_tasks:
                temp_file.write(task_line + '\n')
            
            temp_file_path = temp_file.name
        
        # Get editor command
        editor_cmd = get_editor()
        
        # Open file in editor
        click.echo(f"📝 Opening {len(formatted_tasks)} tasks in {editor_cmd}...")
        click.echo("💡 Toggle checkboxes [ ] ↔ [x] to mark tasks complete/incomplete")
        
        # Split editor command if it contains spaces
        editor_parts = editor_cmd.split()
        result = subprocess.run(editor_parts + [temp_file_path])
        
        if result.returncode != 0:
            click.echo("❌ Editor was closed without saving or an error occurred")
            return
        
        # Read the edited file
        with open(temp_file_path, 'r') as f:
            edited_lines = f.readlines()
        
        # Parse changes and update database
        completed_count = 0
        reopened_count = 0
        
        for line in edited_lines:
            # Skip header lines and empty lines
            if line.startswith('#') or line.strip() == '':
                continue
            
            # Parse the task line
            task_info = parse_task_line(line)
            if not task_info:
                continue
            
            # Find matching task in database
            task_id = find_matching_task(task_info, db_manager)
            if not task_id:
                continue
            
            # Update completion status if changed
            if update_task_completion(task_id, task_info['is_completed'], db_manager):
                if task_info['is_completed']:
                    completed_count += 1
                else:
                    reopened_count += 1
        
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except OSError:
            pass  # File might already be deleted
        
        # Show summary
        total_updated = completed_count + reopened_count
        if total_updated > 0:
            click.echo(f"✅ Updated {total_updated} tasks ({completed_count} completed, {reopened_count} reopened)")
        else:
            click.echo("ℹ️  No changes detected")
            
    except Exception as e:
        click.echo(f"❌ Error editing tasks: {str(e)}", err=True)
        raise click.Abort() 