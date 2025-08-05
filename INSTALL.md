# Fin Installation Guide

This guide will help you install and set up the Fin task management system.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- A modern web browser (for the dashboard)

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd fin
```

### 2. Install the Package

```bash
# Install in development mode
pip install -e .

# Or install globally
pip install .
```

### 3. Initialize the Database

```bash
# Create the database and directory structure
fin init
```

This will:
- Create the `~/fin/` directory
- Initialize the SQLite database at `~/fin/tasks.db`
- Set up the required tables

### 4. Verify Installation

```bash
# Check that the CLI is working
fin --help

# Add a test task
fin "Test task" --label test

# List tasks
fin list-tasks
```

## Web Dashboard Setup

### Option 1: Direct File Access

1. Navigate to the web dashboard directory:
   ```bash
   cd fin-web
   ```

2. Open `index.html` in your browser:
   ```bash
   # On macOS
   open index.html
   
   # On Linux
   xdg-open index.html
   
   # On Windows
   start index.html
   ```

### Option 2: HTTP Server

```bash
# Navigate to the dashboard directory
cd fin-web

# Start a local server
python -m http.server 8000

# Open in browser
open http://localhost:8000
```

## Configuration

### Environment Variables

You can customize the behavior using environment variables:

```bash
# Set custom database path
export FIN_DB_PATH=/path/to/your/tasks.db

# Set default editor for task editing
export EDITOR=nano  # or vim, code, etc.
```

### Editor Configuration

The `fin open-editor` command uses your system's default editor. To set a specific editor:

```bash
# For VS Code
export EDITOR=code

# For Vim
export EDITOR=vim

# For Nano
export EDITOR=nano
```

## Quick Start Examples

### Basic Workflow

```bash
# 1. Add some tasks
fin "Review pull requests" --label work
fin "Update documentation" --label docs
fin "Call client" --label urgent

# 2. List your tasks
fin list-tasks

# 3. Edit tasks in your editor
fin open-editor

# 4. Generate a report
fin report daily
```

### Web Dashboard Workflow

1. **Open the dashboard**: Navigate to `fin-web/` and open `index.html`
2. **Add tasks**: Press `n` to add new tasks
3. **Manage tasks**: Use keyboard shortcuts to navigate and toggle completion
4. **Search and filter**: Use `/` to search and click labels to filter
5. **Save changes**: Click "💾 Save DB" to download the updated database

## Troubleshooting

### Common Issues

**"Command not found: fin"**
```bash
# Make sure the package is installed
pip install -e .

# Check your PATH
which fin

# Try running with python -m
python -m fincli.cli --help
```

**"Database not found"**
```bash
# Initialize the database
fin init

# Check the database location
ls -la ~/fin/tasks.db
```

**"Editor not opening"**
```bash
# Set your preferred editor
export EDITOR=nano

# Or use a specific editor
fin open-editor --editor vim
```

**Web dashboard not loading**
- Ensure you're opening `fin-web/index.html` in a modern browser
- Check that the database file exists at `~/fin/tasks.db`
- Try using a local HTTP server instead of direct file access

### Getting Help

```bash
# General help
fin --help

# Command-specific help
fin add-task --help
fin list-tasks --help
fin open-editor --help

# Check version
fin --version
```

## Development Setup

If you want to contribute to the project:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=fincli --cov-report=html

# Format code
black fincli/ tests/

# Sort imports
isort fincli/ tests/

# Lint code
flake8 fincli/ tests/
```

## Uninstallation

To remove Fin:

```bash
# Uninstall the package
pip uninstall fincli

# Remove the database (optional)
rm -rf ~/fin/
```

## Support

- **Documentation**: See `README.md` for detailed usage
- **Issues**: Report bugs and feature requests on GitHub
- **Tests**: Run `pytest` to verify everything is working

---

**Fin** - Simple, powerful task management for developers and teams. 