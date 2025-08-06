# FinCLI

A lightweight, modular task tracking system with a powerful CLI interface.

## Features

- **Initialize database**: `fin init` (optional - auto-created when needed)
- **Add tasks**: `fin "task description" --label work,urgent`
- **List tasks**: `fins` (today's open + yesterday's completed)
- **Edit tasks**: `fine` (opens in your editor)
- **Manage labels**: `fin-labels` (list all known labels)
- **Import tasks**: `fin-import --source csv` (from external sources)
- **Label filtering**: `fins --label work` or `fine --label urgent`
- **Flexible label syntax**: Comma or space separated, auto-normalized

## Installation

### Local Development Install

```bash
# Clone the repository
git clone <repository-url>
cd fincli

# Install in development mode
pip install -e .

# Test the installation
fin --help
```

### Global Install

```bash
pip install fincli
```

### Database Initialization

```bash
# Initialize the database (optional - auto-created when needed)
fin init

# Initialize with custom database path
fin init --db-path ~/my-tasks.db

# The database is automatically created when you first use any fin command
# So fin init is mainly useful for explicit initialization or custom paths
```

## Usage

### Database Initialization

```bash
# Initialize the database (optional)
fin init

# Initialize with custom path
fin init --db-path ~/my-tasks.db

# Check database status
fin init  # Shows current task count and location
```

### Adding Tasks

```bash
# Basic task
fin "Write documentation"

# With labels
fin "Review pull request" --label work,urgent

# Multiple label arguments
fin "Buy groceries" -l personal -l shopping

# Labels are automatically normalized (lowercase, deduplicated, sorted)
fin "Task with MIXED case LABELS" --label "WORK, urgent Personal"
# → stored as: personal,urgent,work
```

### Listing Tasks

```bash
# Default: today's open + yesterday's completed
fins

# Include completed tasks from past 7 days
fins -d 7

# List open tasks from past week
fins -s open

# List all tasks from past 10 days
fins -s all -d 10

# Add a completed task
fins 'task that is already done'

# Add a completed task with labels
fins 'finished task with labels' -l work -l urgent

# List today and yesterday's open tasks (default)
fin list-tasks

# List today and yesterday's open tasks (alias)
fin list

# List today and yesterday's completed tasks
fin list-tasks -s completed

# List today and yesterday's completed tasks (alias)
fin list-tasks -s done

# List today and yesterday's completed tasks (command alias)
fin list -s completed

# Filter by label
fins --label work
fins --label infra

# Label filtering is case-insensitive and supports partial matches
fins --label automation  # matches "automation", "automation-ops", etc.
```

### Editing Tasks

```bash
# Default: today's open + yesterday's completed
fine

# Filter by label
fine --label work

# Filter by days
fine --days 7

# Filter by date
fine --date 2025-07-28

# Opens in your $EDITOR (defaults to nano/vim/code)
# Toggle checkboxes [ ] ↔ [x] to mark tasks complete/incomplete
```

### Managing Labels

```bash
# List all known labels
fin-labels

# Output example:
# Known labels:
# - automation
# - docs
# - infra
# - planning
# - urgent
# - work
```

## Database

Tasks are stored in `~/fin/tasks.db` with the following schema:

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    labels TEXT,
    source TEXT DEFAULT 'cli'
);
```

## Label System

- **Flexible input**: Labels can be comma or space separated
- **Auto-normalization**: All labels are lowercased, deduplicated, and sorted
- **Case-insensitive filtering**: `fins --label work` matches "work", "WORK", "Work"
- **Partial matching**: `fins --label infra` matches "infra", "infrastructure", "infra-ops"

## Examples

```bash
# Add a complex task with multiple labels
fin "Refactor database schema for better performance" --label "planning, infra, urgent"

# List all work tasks from the past week
fins --label work -d 7

# List open tasks from past week
fins -s open

# List all tasks from past 10 days
fins -s all -d 10

# List today and yesterday's open tasks (default)
fin list-tasks

# List today and yesterday's completed tasks
fin list-tasks -s completed

# Edit today and yesterday's open tasks (default)
fine

# Edit completed tasks from past week
fine -s completed -d 7

# Edit completed tasks from past week (alias)
fine -s done -d 7

# Edit all automation tasks
fine --label automation

# See what labels you've used
fin-labels
```

## Development

### Project Structure

```
fincli/
├── fincli/                    # Python module root
│   ├── __init__.py
│   ├── cli.py                 # Entry point for the CLI
│   ├── db.py                  # SQLite connection + schema
│   ├── tasks.py               # CRUD logic for tasks
│   ├── labels.py              # Label management
│   ├── editor.py              # fine command logic
│   ├── utils.py               # date/time helpers, formatting
│   └── intake/                # Import plugins
│       ├── __init__.py
│       ├── csv_importer.py
│       ├── json_importer.py
│       ├── text_importer.py
│       ├── excel_importer.py
│       └── sheets_importer.py
├── setup.py                   # setuptools config
├── README.md
├── requirements.txt
└── TODO.md
```

### Running Tests

```bash
# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=fincli --cov-report=term-missing
```

### Importing Tasks

**Import from CSV file:**
```bash
# Import from default location (~/fin/tasks.csv)
fin-import --source csv

# Import from specific file
fin-import --source csv --file /path/to/tasks.csv

# Import and delete source file
fin-import --source csv --delete-after-import
```

**Import from JSON file:**
```bash
fin-import --source json --file tasks.json
```

**Import from text file:**
```bash
fin-import --source text --file tasks.txt
```

**Available sources:** csv, json, text, sheets, excel

**File formats:**

**CSV format:**
```csv
Task,Label
"Finish sync script",planning
"Review PR",backend
```

**JSON format:**
```json
[
  {
    "task": "Finish sync script",
    "labels": ["planning", "backend"]
  }
]
```

**Text format:**
```text
Finish sync script,planning
Review PR,backend,urgent
```

## License

MIT License - see LICENSE file for details. 