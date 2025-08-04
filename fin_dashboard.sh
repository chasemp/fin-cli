#!/bin/bash

# Fin Dashboard function
# Add this to your ~/.bashrc or ~/.zshrc:
# source /path/to/fin_dashboard.sh

fin() {
    # Usage: fin [database_path]
    # Example: fin ~/fin/tasks.db
    
    local db_path="${1:-$HOME/fin/tasks.db}"
    local dashboard_dir="$(dirname "$0")"
    
    echo "🚀 Opening Fin Dashboard..."
    echo "📁 Database: $db_path"
    
    # Change to dashboard directory and open
    cd "$dashboard_dir"
    
    if command -v open >/dev/null 2>&1; then
        # macOS
        open "index.html?db=$db_path"
    elif command -v xdg-open >/dev/null 2>&1; then
        # Linux
        xdg-open "index.html?db=$db_path"
    else
        echo "🌐 Open in browser: index.html?db=$db_path"
    fi
    
    echo "✅ Dashboard opened!"
}

# Export the function
export -f fin 