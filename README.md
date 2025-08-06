# FinCLI - A lightweight task tracking system

A simple command-line tool for managing your local task database.

## Quick Start

```bash
# Add a task
fin "my new task"

# Add an important task (shows in Important section)
fin "urgent meeting #i"

# Add a today task (shows in Today section)
fin "daily standup #t"

# List today's tasks with organized sections
fin list

# List completed tasks from last week
fins

# Edit tasks in your editor
fine
```

## Installation

```bash
pip install -e .
```

## Usage

### Adding Tasks

```bash
# Direct task addition
fin "my new task"

# Add with labels
fin "work task #work #urgent"

# Add important task (shows in Important section)
fin "urgent meeting #i"

# Add today task (shows in Today section)
fin "daily standup #t"

# Add task that's both important and for today
fin "critical deadline #i #t"

# Add completed task directly
fins "already done task"

# Add task with due date
fin "project deadline #due:2025-08-10"

# Add recurring task
fin "daily standup #recur:daily"
fin "weekly review #recur:weekly"

# Add task with dependencies
fin "implement feature #depends:task123"
```

### Listing Tasks

Tasks are displayed in organized sections:

```bash
# List today and yesterday's open tasks (default)
fin list

# List with custom date range
fin list -d 7

# List completed tasks
fin list -s completed

# List all tasks (open and completed)
fin list -s all

# Complex label filtering
fin list -l "work and urgent"    # Tasks with both work AND urgent labels
fin list -l "work or personal"   # Tasks with work OR personal labels
fin list -l "urgent"             # Simple label filtering
```

### Priority System

Tasks are organized into sections based on labels:

- **Important** (`#i`): High priority tasks that appear first
- **Today** (`#t`): Tasks marked for today
- **Open**: Regular tasks without priority labels

```bash
# Add important task
fin "urgent meeting #i"

# Add today task
fin "daily standup #t"

# Add regular task
fin "routine task"

# Tasks display in organized sections
fin list
```

### Advanced Features

#### Due Dates
```bash
# Add task with due date
fin "project deadline #due:2025-08-10"

# Due dates are stored as labels for easy filtering
fin list -l "due:2025-08-10"
```

#### Recurring Tasks
```bash
# Add daily recurring task
fin "daily standup #recur:daily"

# Add weekly recurring task
fin "weekly review #recur:weekly"

# Add monthly recurring task
fin "monthly report #recur:monthly"
```

#### Task Dependencies
```bash
# Add task that depends on another
fin "implement feature #depends:task123"

# Dependencies are stored as labels
fin list -l "depends:task123"
```

#### Complex Label Combinations
```bash
# Find tasks with multiple labels (AND)
fin list -l "work and urgent"

# Find tasks with any of several labels (OR)
fin list -l "work or personal"

# Combine multiple criteria
fin list -l "work and urgent" -l "personal"
```

#### Bulk Operations in Editor
```bash
# Edit multiple tasks at once
fine

# In the editor, you can:
# - Mark multiple tasks as complete: [ ] → [x]
# - Reopen multiple tasks: [x] → [ ]
# - Delete multiple tasks: Remove lines
# - Add new tasks: Add lines with [ ] timestamp content
# - Modify task content: Edit the text
```

**Example Output:**
```
Important
1
[ ] 2025-08-06 15:14  Urgent meeting #i

Today
2
[ ] 2025-08-06 15:14  Daily standup #t

Open
3
[ ] 2025-08-06 15:14  Project deadline #due:2025-08-10
4
[ ] 2025-08-06 15:14  Weekly review #recur:weekly
```

### Configuration

FinCLI uses a configuration file at `~/fin/config.json` to customize behavior:

```bash
# View current configuration
fin config

# Enable auto-today for important tasks (default)
fin config --auto-today true

# Disable auto-today for important tasks
fin config --auto-today false

# Set default days for task lists
fin config --default-days 7

# Set default editor
fin config --default-editor vim
```

#### Auto-Today for Important Tasks

By default, important tasks (`#i`) automatically get the today label (`#t`) added. This helps with backlog management by ensuring important tasks appear in today's list.

- **Enabled** (default): Important tasks automatically get `#t` label
- **Disabled**: Important tasks only get `#i` label

Tasks with both `#i` and `#t` appear only in the Important section, not duplicated in Today.

### Task Editing

```bash
# Edit today's tasks in your editor
fine

# Edit with custom date range
fine -d 7

# Edit completed tasks
fine -s completed

# Preview what would be edited
fine --dry-run
```

### Viewing Completed Tasks

```bash
# View recent completed tasks
fins

# View completed tasks from last 30 days
fins -d 30

# Add completed task directly
fins "task I already finished"
```

### Exporting and Importing Tasks

```bash
# Export all tasks to CSV
fin export tasks.csv

# Export to JSON with completion status
fin export tasks.json -f json

# Export to editor-compatible format
fin export tasks.txt -f txt

# Import tasks (auto-detects format)
fin import tasks.csv

# Import with labels
fin import tasks.txt -l work -l urgent

# Import and clear existing tasks
fin import tasks.csv --clear-existing --yes
```

### Backup and Restore

```bash
# Create backup
fin backup

# List backups
fin list-backups

# Restore from backup
fin restore 001

# Restore latest backup
fin restore-latest --yes
```

## Command Reference

| Command | Description |
|---------|-------------|
| `fin "task"` | Add task directly |
| `fin list` | List today's open tasks (organized sections) |
| `fin list -d 7` | List tasks from last 7 days |
| `fin list -s completed` | List completed tasks |
| `fin list -s all` | List all tasks |
| `fine` | Edit tasks in editor |
| `fins` | View completed tasks |
| `fin config` | Manage configuration |
| `fin export file.csv` | Export tasks |
| `fin import file.csv` | Import tasks |
| `fin backup` | Create backup |
| `fin restore 001` | Restore from backup |

## Options

- `-d, --days N` - Show tasks from last N days
- `-s, --status [open\|completed\|done\|all]` - Filter by status
- `-l, --label LABEL` - Filter by label
- `--force, --yes` - Skip confirmation prompts

## Examples

```bash
# Add important task (auto-gets today label)
fin "meeting with client #i"

# Add today task
fin "daily standup #t"

# Add task that's both important and for today
fin "critical deadline #i #t"

# List with organized sections
fin list

# Filter by today label (shows important + today tasks)
fin list -l t

# Edit important tasks
fine

# Export important tasks
fin export priority.csv

# Import with priority labels
fin import tasks.csv -l i -l t

# Configure auto-today behavior
fin config --auto-today false
```

## Configuration

The database is stored at `~/fin/tasks.db` by default. Set `FIN_DB_PATH` environment variable to use a different location.

Configuration is stored at `~/fin/config.json` and includes:

- `auto_today_for_important`: Auto-add today label to important tasks (default: true)
- `show_sections`: Show organized sections in task lists (default: true)
- `default_days`: Default number of days for task lists (default: 1)
- `default_editor`: Default editor for task editing (default: system default)

**Note**: The config file is created automatically on first use with default values. Existing configurations are preserved and never overwritten during installation or updates. 