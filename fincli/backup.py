"""
Backup and recovery system for fin-cli database.
Maintains the last 10 database states with rollback capability.
"""

from datetime import datetime
import os
from pathlib import Path
import shutil
import sqlite3
from typing import List, Optional


class DatabaseBackup:
    """Manages database backups with rollback capability."""

    def __init__(self, db_path: str, max_backups: int = 10):
        """
        Initialize backup system.

        Args:
            db_path: Path to the main database
            max_backups: Maximum number of backups to keep
        """
        self.db_path = db_path
        self.max_backups = max_backups
        self.backup_dir = self._get_backup_dir()
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _get_backup_dir(self) -> Path:
        """Get the backup directory path."""
        db_path = Path(self.db_path)
        return db_path.parent / f"{db_path.stem}_backups"

    def _get_backup_path(self, backup_id: int) -> Path:
        """Get path for a specific backup."""
        return self.backup_dir / f"backup_{backup_id:03d}.db"

    def _get_metadata_path(self, backup_id: int) -> Path:
        """Get path for backup metadata."""
        return self.backup_dir / f"backup_{backup_id:03d}.meta"

    def create_backup(self, description: str = "", task_changes: Optional[dict] = None) -> int:
        """
        Create a new backup of the current database.

        Args:
            description: Optional description of what changed
            task_changes: Optional dict with details about what tasks changed

        Returns:
            Backup ID of the created backup
        """
        if not os.path.exists(self.db_path):
            return -1  # No database to backup

        # Get next backup ID
        backup_id = self._get_next_backup_id()

        # Create backup
        backup_path = self._get_backup_path(backup_id)
        shutil.copy2(self.db_path, backup_path)

        # Create metadata with enhanced information
        metadata = {
            "backup_id": backup_id,
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "original_path": str(self.db_path),
            "task_count": self._get_task_count(self.db_path),
        }

        # Add task change details if provided
        if task_changes:
            metadata["task_changes"] = task_changes
            metadata["change_summary"] = {
                "completed": task_changes.get("completed_count", 0),
                "reopened": task_changes.get("reopened_count", 0),
                "new": task_changes.get("new_tasks_count", 0),
                "content_modified": task_changes.get("content_modified_count", 0),
                "deleted": task_changes.get("deleted_count", 0),
            }

        self._save_metadata(backup_id, metadata)

        # Clean up old backups
        self._cleanup_old_backups()

        return backup_id

    def _get_next_backup_id(self) -> int:
        """Get the next available backup ID."""
        existing_backups = self._list_backup_ids()
        if not existing_backups:
            return 1
        return max(existing_backups) + 1

    def _list_backup_ids(self) -> List[int]:
        """List all existing backup IDs."""
        if not self.backup_dir.exists():
            return []

        backup_ids = []
        for file in self.backup_dir.glob("backup_*.db"):
            try:
                backup_id = int(file.stem.split("_")[1])
                backup_ids.append(backup_id)
            except (ValueError, IndexError):
                continue

        return sorted(backup_ids)

    def _get_task_count(self, db_path: str) -> int:
        """Get the number of tasks in the database."""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tasks")
                return cursor.fetchone()[0]
        except Exception:
            return 0

    def _save_metadata(self, backup_id: int, metadata: dict):
        """Save backup metadata."""
        import json

        meta_path = self._get_metadata_path(backup_id)
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _load_metadata(self, backup_id: int) -> Optional[dict]:
        """Load backup metadata."""
        import json

        meta_path = self._get_metadata_path(backup_id)
        if not meta_path.exists():
            return None

        try:
            with open(meta_path, "r") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def _cleanup_old_backups(self):
        """Remove old backups beyond max_backups limit."""
        backup_ids = self._list_backup_ids()
        if len(backup_ids) <= self.max_backups:
            return

        # Remove oldest backups
        to_remove = backup_ids[: -self.max_backups]
        for backup_id in to_remove:
            self._remove_backup(backup_id)

    def _remove_backup(self, backup_id: int):
        """Remove a specific backup."""
        backup_path = self._get_backup_path(backup_id)
        meta_path = self._get_metadata_path(backup_id)

        if backup_path.exists():
            backup_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

    def list_backups(self) -> List[dict]:
        """
        List all available backups with metadata.

        Returns:
            List of backup metadata dictionaries
        """
        backups = []
        for backup_id in self._list_backup_ids():
            metadata = self._load_metadata(backup_id)
            if metadata:
                backups.append(metadata)

        return sorted(backups, key=lambda x: x["backup_id"], reverse=True)

    def rollback(self, backup_id: int) -> bool:
        """
        Rollback to a specific backup.

        Args:
            backup_id: ID of the backup to rollback to

        Returns:
            True if rollback successful, False otherwise
        """
        backup_path = self._get_backup_path(backup_id)
        if not backup_path.exists():
            return False

        # Create a backup of current state before rollback
        current_backup_id = self.create_backup("Auto-backup before rollback")

        try:
            # Restore the backup
            shutil.copy2(backup_path, self.db_path)
            return True
        except Exception as e:
            # If rollback fails, try to restore the current state
            if current_backup_id > 0:
                current_backup_path = self._get_backup_path(current_backup_id)
                if current_backup_path.exists():
                    shutil.copy2(current_backup_path, self.db_path)
            raise e

    def get_latest_backup_id(self) -> Optional[int]:
        """Get the ID of the latest backup."""
        backup_ids = self._list_backup_ids()
        return max(backup_ids) if backup_ids else None

    def get_restore_preview(self, backup_id: int) -> Optional[dict]:
        """
        Get a preview of what will change when restoring to a specific backup.

        Args:
            backup_id: ID of the backup to preview

        Returns:
            Dictionary with preview information or None if backup not found
        """
        backup_path = self._get_backup_path(backup_id)
        if not backup_path.exists():
            return None

        try:
            # Get current task count and sample tasks
            current_tasks = self._get_task_summary(self.db_path)
            backup_tasks = self._get_task_summary(backup_path)

            # Calculate differences
            preview = {"backup_id": backup_id, "current_state": current_tasks, "backup_state": backup_tasks, "changes": {"tasks_added": backup_tasks["total"] - current_tasks["total"], "tasks_removed": current_tasks["total"] - backup_tasks["total"], "sample_current": current_tasks.get("sample_tasks", []), "sample_backup": backup_tasks.get("sample_tasks", [])}}

            return preview

        except Exception:
            return None

    def _get_task_summary(self, db_path: str) -> dict:
        """Get a summary of tasks in a database."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get total task count
            cursor.execute("SELECT COUNT(*) FROM tasks")
            total_tasks = cursor.fetchone()[0]

            # Get sample of recent tasks
            cursor.execute(
                """
                SELECT id, content, completed_at, created_at 
                FROM tasks 
                ORDER BY created_at DESC 
                LIMIT 5
            """
            )
            sample_tasks = []
            for row in cursor.fetchall():
                sample_tasks.append({"id": row[0], "content": row[1][:50] + "..." if len(row[1]) > 50 else row[1], "completed": bool(row[2]), "created": row[3]})

            conn.close()

            return {"total": total_tasks, "sample_tasks": sample_tasks}

        except Exception:
            return {"total": 0, "sample_tasks": []}

    def restore_latest(self) -> bool:
        """Restore to the latest backup."""
        latest_id = self.get_latest_backup_id()
        if latest_id is None:
            return False
        return self.rollback(latest_id)
