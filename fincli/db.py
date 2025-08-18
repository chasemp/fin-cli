"""
Database module for FinCLI

Handles SQLite connection and schema management.
"""

import os
from pathlib import Path
import sqlite3
from typing import Optional


class DatabaseManager:
    """Manages SQLite database connection and schema."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            db_path: Optional custom database path. Defaults to ~/fin/tasks.db
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Check for environment variable first
            env_db_path = os.environ.get("FIN_DB_PATH")
            if env_db_path:
                self.db_path = Path(env_db_path)
            else:
                # Default to ~/fin/tasks.db
                self.db_path = Path.home() / "fin" / "tasks.db"

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

        # Only print path if verbose mode is enabled
        if os.environ.get("FIN_VERBOSE") == "1":
            print("DatabaseManager using path:", self.db_path)

    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create tasks table if it doesn't exist
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    labels TEXT,
                    source TEXT DEFAULT 'cli'
                )
            """
            )

            # Check if modified_at column exists, add it if it doesn't
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [column[1] for column in cursor.fetchall()]

            if "modified_at" not in columns:
                # SQLite doesn't allow non-constant defaults in ALTER TABLE
                # So we add the column without a default
                cursor.execute("ALTER TABLE tasks ADD COLUMN modified_at TIMESTAMP")

                # Update existing tasks to have modified_at = created_at
                cursor.execute("UPDATE tasks SET modified_at = created_at WHERE modified_at IS NULL")

            # Check if due_date column exists, add it if it doesn't
            if "due_date" not in columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")

                # Create index on due_date for efficient filtering
                try:
                    cursor.execute("CREATE INDEX idx_tasks_due_date ON tasks(due_date)")
                except sqlite3.OperationalError:
                    # Index might already exist
                    pass

            # Check if context column exists, add it if it doesn't
            if "context" not in columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN context TEXT DEFAULT 'default'")

                # Create index on context for efficient filtering
                try:
                    cursor.execute("CREATE INDEX idx_tasks_context ON tasks(context)")
                except sqlite3.OperationalError:
                    # Index might already exist
                    pass

            conn.commit()

    def get_connection(self):
        """Get a database connection."""
        import contextlib

        @contextlib.contextmanager
        def connection_context():
            conn = sqlite3.connect(self.db_path)
            try:
                yield conn
            finally:
                conn.close()

        return connection_context()

    def _init_mock_db(self, db_path):
        """Helper method for testing - initialize with custom path."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

        # Only print path if verbose mode is enabled
        if os.environ.get("FIN_VERBOSE") == "1":
            print("DatabaseManager using path:", self.db_path)
