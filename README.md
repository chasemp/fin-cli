# Fin - Task Management System

A lightweight, modular task tracking system with a powerful CLI interface and web dashboard.

## Features

- **CLI Interface**: Add, list, and manage tasks from the command line
- **Web Dashboard**: Browser-based interface with SQLite via WebAssembly
- **Label Management**: Organize tasks with tags and labels
- **Analytics**: Track productivity with detailed reports and digests
- **Import System**: Import tasks from CSV, JSON, and text files
- **Offline Support**: Works entirely offline with local SQLite storage

## Quick Start

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd fin
   ```

2. **Install the package:**
   ```bash
   pip install -e .
   ```

3. **Initialize the database:**
   ```bash
   fin init
   ```

### Basic Usage

#### Adding Tasks
```bash
# Add a simple task
fin "Complete project documentation"

# Add a task with labels
fin "Review pull requests" --label work --label urgent

# Add a task with multiple labels (shorthand)
fin "Update dependencies" -l maintenance -l backend

# Add a task directly (shortcut for add-task)
fin "Complete project documentation"
```

#### Listing Tasks
```bash
# List today and yesterday's open tasks (default)
fin list-tasks

# List today and yesterday's completed tasks
fin list-tasks --status completed

# List today and yesterday's all tasks (open + completed)
fin list-tasks --status all

# List completed tasks from past week (shortcut)
fins

# List open tasks from past week
fins --status open

# List all tasks from past 10 days
fins --status all --days 10

# Edit today and yesterday's open tasks (default)
fine

# Edit completed tasks from past week
fine --status completed --days 7

# List tasks with labels
fin list-tasks --label work

# List tasks from the past 30 days
fin list-tasks --days 30

# List completed tasks from the past week
fin list-tasks --status completed --days 7
```

#### Editing Tasks
```bash
# Open tasks in your default editor
fin open-editor

# Edit only work tasks
fin open-editor --label work

# Edit tasks from the past week
fin open-editor --days 7

# Edit tasks from a specific date
fin open-editor --date 2025-01-15
```

#### Managing Labels
```bash
# List all known labels
fin list-labels

# Filter tasks by label
fin list-tasks --label urgent
```

### Web Dashboard

1. **Open the dashboard:**
   ```bash
   # Navigate to the web directory
   cd fin-web
   
   # Open index.html in your browser
   open index.html
   ```

2. **Dashboard Features:**
   - View tasks grouped by date
   - Add new tasks with the `n` key
   - Search and filter tasks
   - Toggle task completion
   - Keyboard shortcuts for quick navigation

### Analytics and Reports

```bash
# Generate daily digest
fin digest daily

# Generate weekly report in Markdown
fin report weekly --format markdown

# Export analytics to CSV
fin report monthly --format csv
```

## Advanced Features

### Importing Tasks

```bash
# Import from CSV file
fin import csv sample_tasks.csv

# Import from JSON file
fin import json sample_tasks.json

# Import from text file
fin import text sample_tasks.txt
```

### Database Management

The system uses SQLite for data storage. By default, the database is located at:
- **CLI**: `~/fin/tasks.db`
- **Web Dashboard**: Uses the same database location

### Configuration

Environment variables:
- `FIN_DB_PATH`: Custom database path
- `EDITOR`: Default editor for task editing

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=fincli --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m cli
```

### Code Quality

```bash
# Format code
black fincli/ tests/

# Sort imports
isort fincli/ tests/

# Lint code
flake8 fincli/ tests/
```

### Project Structure

```
fin/
├── fincli/                 # Main Python package
│   ├── fincli/
│   │   ├── cli.py        # CLI commands
│   │   ├── db.py         # Database management
│   │   ├── tasks.py      # Task operations
│   │   ├── labels.py     # Label management
│   │   ├── editor.py     # Editor integration
│   │   ├── analytics.py  # Analytics and reporting
│   │   ├── utils.py      # Utility functions
│   │   └── intake/       # Import modules
│   └── setup.py          # Package configuration
├── fin-web/              # Web dashboard
│   ├── index.html        # Main dashboard
│   ├── app.js           # Dashboard logic
│   └── style.css        # Styling
├── tests/               # Test suite
└── README.md           # This file
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `fin init` | Initialize the database |
| `fin add-task <content>` | Add a new task |
| `fin <content>` | Add a new task (shortcut) |
| `fin list-tasks` | List all tasks |
| `fin open-editor` | Edit tasks in external editor |
| `fine` | Edit tasks in external editor (shortcut) |
| `fins` | List completed tasks from past week (shortcut) |
| `fin list-labels` | List all known labels |
| `fin digest <period>` | Generate digest report |
| `fin report <period>` | Generate detailed report |
| `fin import <format> <file>` | Import tasks from file |

### Command Options

- `--label, -l`: Add labels to tasks
- `--days`: Show tasks from past N days (default: 1 for today and yesterday)
- `--status`: Filter by status (open, completed, all)
- `--format`: Output format (text, markdown, html, csv)
- `--date`: Filter by specific date

## Keyboard Shortcuts (Web Dashboard)

| Key | Action |
|-----|--------|
| `n` | Add new task |
| `s` | Search tasks |
| `/` | Focus search |
| `↑/↓` | Navigate tasks |
| `Space` | Toggle completion |
| `Esc` | Close modal/cancel |
| `Cmd+Shift+R` | Hard reload |
| `?` | Show help |

## Examples

### Workflow Examples

**Daily Task Management:**
```bash
# Add today's tasks
fin "Review email backlog" -l work
fin "Update project documentation" -l docs
fin "Call client about requirements" -l urgent

# List today's work tasks
fin list-tasks --label work

# Edit tasks in editor
fin open-editor
```

**Weekly Planning:**
```bash
# Add weekly goals
fin "Plan sprint tasks" -l planning
fin "Review team performance" -l management
fin "Update dependencies" -l maintenance

# Generate weekly report
fin report weekly --format markdown
```

**Import from External Sources:**
```bash
# Import from CSV
fin import csv tasks.csv

# Import from project management tool
fin import json jira_export.json
```

## Troubleshooting

### Common Issues

**Database not found:**
```bash
fin init
```

**Editor not opening:**
```bash
export EDITOR=nano  # or vim, code, etc.
```

**Web dashboard not loading:**
- Ensure you're opening `fin-web/index.html` in a modern browser
- Check that the database file exists at `~/fin/tasks.db`

### Getting Help

- Run `fin --help` for command overview
- Run `fin <command> --help` for specific command help
- Check the test suite for usage examples

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

[Add your license information here]

---

**Fin** - Simple, powerful task management for developers and teams. 