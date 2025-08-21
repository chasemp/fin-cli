# FinCLI - A lightweight task tracking system

A simple command-line tool for managing your local task database with enhanced filtering, task modification tracking, and flexible status management.

## Quick Start

```bash
# Add a task
fin "my new task"

# Add important task (shows in Important section)
fin "urgent meeting #i"

# List all open tasks
fin

# Edit tasks in your editor
fine

# View completed tasks
fins

# Quick filtering
fin -s a          # All tasks
fin -s o          # Open only
fin -s d          # Done only
fin -t            # Today only
```

## Installation

```bash
pip install -e .
```

## Common Patterns

### **Daily Workflow**
```bash
# Start your day - see what's open
fin

# Add today's priorities
fin "morning standup #t"
fin "review PRs #t #work"

# Check what's completed recently
fins

# End of day - mark things complete
fine -s o
```

### **Weekly Review**
```bash
# See what was accomplished this week
fins -d 7

# Review all open tasks
fine -s o --dry-run

# Plan next week
fine -s o -d 0 --dry-run
```

### **Project Management**
```bash
# Focus on specific project
fin list -l "project-name"

# See project progress
fin list -l "project-name" -s "o,d"

# Export project tasks
fin export project.csv -l "project-name"
```

### **Context Management**
```bash
# Switch to work context
fin -c work

# Add tasks in work context
fin "review code #urgent"

# Switch to personal context
fin -c personal

# Add personal tasks
fin "grocery shopping"

# List available contexts
fin context list

# Show tasks in specific context
fin context show work

# Create new context
fin context create project-a

# Delete context (with safety checks)
fin context delete old-project --force
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

**Note:** The words `and`, `or`, `ref`, `due`, `recur`, `depends`, and `not` are reserved and cannot be used as labels. Use complex filtering instead: `fin list -l "work and urgent"`, or use special patterns: `fin "project deadline #due:2025-08-10"`.

### Listing Tasks

Tasks are displayed in organized sections with enhanced filtering options:

```bash
# List all open tasks (default behavior)
fin

# List with custom date range
fin -d 7

# List with status filtering
fin -s completed
fin -s "done,open"
fin -s "open, done"

# List with both date and status
fin -d 3 -s "done,open"

# List all time (no date restriction, limited by max_limit)
fin -d 0

# List with verbose output
fin -v
fin -d 7 -s "done,open" -v

# Complex label filtering
fin -l "work and urgent"    # Tasks with both work AND urgent labels
fin -l "work or personal"   # Tasks with work OR personal labels
fin -l "urgent"             # Simple label filtering
```

### Enhanced Status Filtering (`-s` flag)

The `-s` flag accepts comma-separated status values with flexible spacing:

```bash
# Single status
fin -s done
fin -s open

# Multiple statuses (any of these)
fin -s "done,open"
fin -s "done, open"
fin -s "done , open"

# Combine with date filtering
fin -d 7 -s "done,open"
fin -d 0 -s completed  # All completed tasks from all time
```

### Date Filtering (`-d` flag)

```bash
# Default: today and yesterday
fin

# Last N days (including today)
fin -d 3
fin -d 7

# All time (no date restriction, limited by max_limit)
fin -d 0

# Weekdays only (configurable)
fin -d 5  # Last 5 weekdays
```

### Max Limit and Warnings

All commands respect a `max_limit` parameter (default: 100) to prevent overwhelming output:

```bash
# When max_limit is hit, a warning is shown
fin -v  # Shows "Max limit: 100" and "Total available: X"

# For fin command, warnings appear even without -v when open tasks exceed limit
fin  # Shows warning if more than 100 open tasks exist
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

#### Contexts
Contexts allow you to organize tasks by project, work area, or any other grouping. Once set, all commands filter tasks by the current context.

```bash
# Set context for current session
fin -c work

# All subsequent commands use work context
fin list                    # Shows only work tasks
fin add-task "meeting"     # Creates task in work context

# Switch to different context
fin -c personal

# Now all commands use personal context
fin list                    # Shows only personal tasks

# Manage contexts
fin context list            # List all available contexts
fin context create project-a # Create new context
fin context show work       # Show tasks in work context
fin context delete old      # Delete context (with safety checks)
```

**Context Rules:**
- Context is session-based (persists in current shell)
- Default context is 'default' when none is set
- Tasks automatically get current context upon creation
- Context filtering works with all other filters (labels, dates, status)

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

# Exclude tasks with specific labels (NOT)
fin list -l "NOT urgent"
fin list -l "work AND NOT urgent"

# Complex boolean combinations
fin list -l "family AND work AND NOT love"
fin list -l "NOT urgent OR personal"
fin list -l "work AND (urgent OR important)"

# Combine multiple criteria
fin list -l "work and urgent" -l "personal"
```

#### Reserved Words
The following words are reserved and cannot be used as labels because they're used for complex filtering or special patterns:
- `and` - Used for AND logic in filtering
- `or` - Used for OR logic in filtering
- `ref` - Used in task references (`#ref:task123`)
- `due` - Used in due date patterns (`#due:2025-08-10`)
- `recur` - Used in recurring task patterns (`#recur:daily`)
- `depends` - Used in dependency patterns (`#depends:task123`)
- `not` - Used for NOT logic in filtering (`NOT urgent`, `work AND NOT urgent`)

**Example:**
```bash
# ❌ These will fail
fin "Task with reserved label #and"
fin "Task with reserved label #ref"
fin "Task with reserved label #due"

# ✅ Use complex filtering instead
fin list -l "work and urgent"

# ✅ Use special patterns
fin "project deadline #due:2025-08-10"
fin "daily standup #recur:daily"
fin "implement feature #depends:task123"

# ✅ Use NOT logic
fin list -l "NOT urgent"
fin list -l "work AND NOT urgent"
```

#### Bulk Operations in Editor
```bash
# Edit all open tasks
fine

# Edit tasks from last 3 days
fine -d 3

# Edit completed tasks from last 3 days
fine -d 3 -s done

# Edit all time completed tasks (limited by max_limit)
fine -d 0 -s done

# Preview what would be edited
fine --dry-run
```

**In the editor, you can:**
- Mark multiple tasks as complete: `[ ]` → `[x]`
- Reopen multiple tasks: `[x]` → `[ ]`
- Delete multiple tasks: Remove lines
- Add new tasks: Add lines with `[ ] timestamp content`
- Modify task content: Edit the text (tracks `modified_at`)

**Example Output:**
```
Important
1 [ ] 2025-08-06 15:14  Urgent meeting #i

Today
2 [ ] 2025-08-06 15:14  Daily standup #t

Open
3 [ ] 2025-08-06 15:14  Project deadline #due:2025-08-10
4 [ ] 2025-08-06 15:14  Weekly review #recur:weekly
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

# Configure weekday-only lookback
fin config --weekdays-only true
```

#### Auto-Today for Important Tasks

By default, important tasks (`#i`) automatically get the today label (`#t`) added. This helps with backlog management by ensuring important tasks appear in today's list.

- **Enabled** (default): Important tasks automatically get `#t` label
- **Disabled**: Important tasks only get `#i` label

Tasks with both `#i` and `#t` appear only in the Important section, not duplicated in Today.

### Task Editing

```bash
# Edit all open tasks in your editor
fine

# Edit with custom date range
fine -d 7

# Edit completed tasks
fine -s completed

# Edit all time completed tasks
fine -d 0 -s done

# Preview what would be edited
fine --dry-run
```

### Viewing Completed Tasks

```bash
# View recent completed tasks (default: today and yesterday)
fins

# View completed tasks from last N days
fins -d 30

# View all time completed tasks (limited by max_limit)
fins -d 0

# View with status filtering
fins -s "done,open"

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

**Enhanced Backup System:**
- Automatic backups before and after editor sessions
- Tracks task changes: completed, reopened, new, content_modified, deleted
- Change summaries in backup metadata

## Command Reference

| Command | Description |
|---------|-------------|
| `fin "task"` | Add task directly |
| `fin` | List all open tasks (organized sections) |
| `fin -d 7` | List tasks from last 7 days |
| `fin -s completed` | List completed tasks |
| `fin -s "done,open"` | List both completed and open tasks |
| `fin -d 0` | List all time (limited by max_limit) |
| `fine` | Edit tasks in editor |
| `fine -d 3 -s done` | Edit completed tasks from last 3 days |
| `fins` | View completed tasks |
| `fins -d 0` | View all time completed tasks |
| `fin config` | Manage configuration |
| `fin export file.csv` | Export tasks |
| `fin import file.csv` | Import tasks |
| `fin backup` | Create backup |
| `fin restore 001` | Restore from backup |

## Options

- `-d, --days N` - Show tasks from last N days (use 0 for all time)
- `-s, --status STATUS` - Filter by status: open/o, completed, done/d, all/a, or comma-separated list
- `-l, --label LABEL` - Filter by label
- `--max-limit N` - Maximum number of tasks to show (default: 100)
- `-t, --today` - Show only today's tasks (overrides days)
- `--verbose, -v` - Show verbose output including filtering details
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
fin

# Filter by status combinations
fin -s "done,open"
fin -s "done, open"

# Filter by status using shorthand letters
fin -s "d,o"      # Same as "done,open"
fin -s a          # Same as "all" (open + completed)
fin -s o          # Same as "open" only
fin -s d          # Same as "done" only

# Filter by date and status
fin -d 7 -s "done,open"

# List all time with verbose output
fin -d 0 -v

# Edit tasks from last week
fine -d 7

# Edit completed tasks from last 3 days
fine -d 3 -s done

# Edit tasks using status shorthand
fine -s a --dry-run      # All tasks (open + completed)
fine -s o --dry-run      # Open tasks only
fine -s d --dry-run      # Done tasks only
fine -s "o,d" --dry-run  # Both open and done

# Edit today's tasks (using shorthand)
fine -t --dry-run

# List today's tasks (using shorthand)
fin list -t --verbose

# View today's completed tasks (using shorthand)
fins -t

# View today's all tasks (both open and completed)
fins -t --status all

# View tasks using status shorthand
fins -s a          # All tasks (open + completed)
fins -s o          # Open tasks only
fins -s d          # Done tasks only
fins -s "o,d"      # Both open and done

# View all time completed tasks
fins -d 0 -v

# Export with filtering
fin export priority.csv -l "i,t"

# Import with priority labels
fin import tasks.csv -l i -l t

# Configure weekday-only lookback
fin config --weekdays-only true
```

## Configuration

The database is stored at `~/fin/tasks.db` by default. Set `FIN_DB_PATH` environment variable to use a different location.

Configuration is stored at `~/fin/config.json` and includes:

- `auto_today_for_important`: Auto-add today label to important tasks (default: true)
- `show_sections`: Show organized sections in task lists (default: true)
- `default_days`: Default number of days for task lists (default: 1)
- `default_editor`: Default editor for task editing (default: system default)
- `weekdays_only_lookback`: Count only weekdays for date filtering (default: true)
- `show_all_open_by_default`: Show all open tasks by default instead of recent ones (default: true)

**Note**: The config file is created automatically on first use with default values. Existing configurations are preserved and never overwritten during installation or updates.

### Advanced Boolean Label Filtering

The label filtering system supports full boolean logic with JQL-inspired syntax:

#### Basic Operators
- **AND**: All labels must be present (`work AND urgent`)
- **OR**: Any label can be present (`work OR personal`) 
- **NOT**: Exclude tasks with specific labels (`NOT urgent`, `work AND NOT urgent`)

#### Complex Expressions
```bash
# Exclude urgent tasks
fin list -l "NOT urgent"

# Work tasks that are not urgent
fin list -l "work AND NOT urgent"

# Family or work tasks, but not urgent ones
fin list -l "(family OR work) AND NOT urgent"

# Triple combination
fin list -l "family AND work AND NOT love"
```

#### Operator Precedence
1. **NOT** has highest precedence
2. **AND** has higher precedence than **OR**
3. Use parentheses for explicit grouping when needed

#### Examples by Use Case
```bash
# Personal tasks only (exclude work)
fin list -l "personal AND NOT work"

# High priority work (urgent + important, but not blocked)
fin list -l "work AND urgent AND important AND NOT blocked"

# Either urgent or due soon, but not completed
fin list -l "(urgent OR due_soon) AND NOT completed"

# All tasks except archived ones
fin list -l "NOT archived"
```

**Note**: The words `and`, `or`, `ref`, `due`, `recur`, `depends`, and `not` are reserved and cannot be used as labels because they're used for complex filtering or special patterns.

## Task Modification Tracking

FinCLI tracks three distinct dates for all tasks:

- **`created_at`**: When the task was first created
- **`modified_at`**: When the task content was last modified (via `fine` editor)
- **`completed_at`**: When the task was marked as completed

This provides a complete audit trail, including tasks modified after completion. The `modified_at` timestamp is automatically updated whenever:
- Task content is changed via the editor
- Task completion status changes
- Task is reopened

## Verbose Output

Use the `-v` flag to see detailed information about filtering criteria:

```bash
fin -v
# Output:
# 🔍 Filtering criteria:
#    • Days: 2 (default: today and yesterday)
#    • Status: open
#    • Max limit: 100
#    • Weekdays only: True (Monday-Friday)
# DatabaseManager using path: /path/to/tasks.db
``` 