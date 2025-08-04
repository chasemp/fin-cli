"""
Database manager for Fin task tracking system
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager with optional custom path."""
        if db_path is None:
            # Check for environment variable first
            env_db_path = os.environ.get('FIN_DB_PATH')
            if env_db_path:
                db_path = env_db_path
            else:
                # Default to ~/.fin/tasks.db
                home_dir = Path.home()
                fin_dir = home_dir / ".fin"
                fin_dir.mkdir(exist_ok=True)
                db_path = fin_dir / "tasks.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_mock_db(self, db_path: str):
        """Initialize database for testing with explicit path."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database and create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create tasks table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    labels TEXT NULL,
                    source TEXT DEFAULT 'cli'
                )
            """)
            
            conn.commit()
    
    def add_task(self, content: str, labels: Optional[List[str]] = None, source: str = "cli") -> int:
        """
        Add a new task to the database.
        
        Args:
            content: The task description (markdown-formatted)
            labels: Optional list of labels (will be stored as lowercase, comma-separated)
            source: Source of the task (default: "cli")
        
        Returns:
            The ID of the newly created task
        """
        # Normalize labels
        labels_str = None
        if labels:
            # Normalize labels: split on comma or space, lowercase, trim whitespace
            import re
            all_labels = []
            for label_group in labels:
                if label_group:
                    # Split on comma or space, then normalize each label
                    split_labels = re.split(r'[, ]+', label_group.strip())
                    for label in split_labels:
                        if label.strip():
                            all_labels.append(label.strip().lower())
            
            # Remove duplicates and sort
            unique_labels = sorted(list(set(all_labels)))
            labels_str = ",".join(unique_labels) if unique_labels else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO tasks (content, labels, source)
                VALUES (?, ?, ?)
            """, (content, labels_str, source))
            
            task_id = cursor.lastrowid
            conn.commit()
            
            return task_id
    
    def get_task(self, task_id: int) -> Optional[dict]:
        """Get a task by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, content, created_at, completed_at, labels, source
                FROM tasks
                WHERE id = ?
            """, (task_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'content': row[1],
                    'created_at': row[2],
                    'completed_at': row[3],
                    'labels': row[4].split(',') if row[4] else [],
                    'source': row[5]
                }
            return None
    
    def list_tasks(self, include_completed: bool = True) -> List[dict]:
        """List all tasks, optionally including completed ones."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, content, created_at, completed_at, labels, source
                FROM tasks
            """
            
            if not include_completed:
                query += " WHERE completed_at IS NULL"
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query)
            
            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'id': row[0],
                    'content': row[1],
                    'created_at': row[2],
                    'completed_at': row[3],
                    'labels': row[4].split(',') if row[4] else [],
                    'source': row[5]
                })
            
            return tasks
    
    def get_all_labels(self) -> List[str]:
        """Get all unique labels from all tasks."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT labels FROM tasks WHERE labels IS NOT NULL AND labels != ''
            """)
            
            all_labels = []
            for row in cursor.fetchall():
                if row[0]:
                    labels = row[0].split(',')
                    all_labels.extend([label.strip() for label in labels if label.strip()])
            
            # Remove duplicates and sort
            return sorted(list(set(all_labels)))
    
    def filter_tasks_by_label(self, label: str, include_completed: bool = True) -> List[dict]:
        """
        Filter tasks by label (case-insensitive, partial match).
        
        Args:
            label: Label to filter by (case-insensitive)
            include_completed: Whether to include completed tasks
            
        Returns:
            List of tasks that match the label
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, content, created_at, completed_at, labels, source
                FROM tasks
                WHERE labels LIKE ?
            """
            
            if not include_completed:
                query += " AND completed_at IS NULL"
            
            query += " ORDER BY created_at DESC"
            
            # Use case-insensitive pattern matching
            pattern = f"%{label.lower()}%"
            cursor.execute(query, (pattern,))
            
            tasks = []
            for row in cursor.fetchall():
                task_labels = row[4].split(',') if row[4] else []
                # Additional check for exact label match (case-insensitive)
                if any(label.lower() in task_label.lower() for task_label in task_labels):
                    tasks.append({
                        'id': row[0],
                        'content': row[1],
                        'created_at': row[2],
                        'completed_at': row[3],
                        'labels': task_labels,
                        'source': row[5]
                    })
            
            return tasks 