#!/bin/bash

# Fin Dashboard Launcher
# Usage: ./open_dashboard.sh [database_path]
# Example: ./open_dashboard.sh ~/fin/tasks.db

# Default database path
DEFAULT_DB_PATH="$HOME/fin/tasks.db"
DB_PATH="${1:-$DEFAULT_DB_PATH}"

# Get the absolute path
ABSOLUTE_DB_PATH=$(realpath "$DB_PATH" 2>/dev/null || echo "$DB_PATH")

echo "🚀 Opening Fin Dashboard..."
echo "📁 Database: $ABSOLUTE_DB_PATH"

# Open dashboard in default browser with database path as parameter
if command -v open >/dev/null 2>&1; then
    # macOS
    open "index.html?db=$ABSOLUTE_DB_PATH"
elif command -v xdg-open >/dev/null 2>&1; then
    # Linux
    xdg-open "index.html?db=$ABSOLUTE_DB_PATH"
else
    echo "🌐 Open in browser: index.html?db=$ABSOLUTE_DB_PATH"
fi

echo "✅ Dashboard opened!"
echo "💡 The dashboard will show the database path and prompt you to load it" 