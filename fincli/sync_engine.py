"""
Sync Engine for FinCLI

Handles synchronization between local tasks and remote systems based on authority types.
"""

from dataclasses import asdict
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple

from .db import DatabaseManager
from .remote_models import (
    RemoteSystemType,
    RemoteTask,
    RemoteTaskValidator,
    TaskAuthority,
    TaskMapper,
    TaskMappingResult,
)
from .tasks import TaskManager

logger = logging.getLogger(__name__)


class SyncEngine:
    """Engine for synchronizing tasks between local database and remote systems."""

    def __init__(self, db_manager: DatabaseManager, task_manager: TaskManager):
        """
        Initialize the sync engine.

        Args:
            db_manager: Database manager instance
            task_manager: Task manager instance
        """
        self.db_manager = db_manager
        self.task_manager = task_manager

    def sync_remote_tasks(
        self,
        remote_tasks: List[RemoteTask],
        system_type: RemoteSystemType,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Synchronize remote tasks with local database.

        Args:
            remote_tasks: List of remote tasks to sync
            system_type: Type of remote system
            dry_run: If True, don't make actual changes

        Returns:
            Dictionary with sync results
        """
        logger.info(f"Starting sync for {len(remote_tasks)} tasks from {system_type.value}")

        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")

        # Initialize task mapper
        mapper = TaskMapper(system_type)

        # Track sync results
        results = {
            "total_tasks": len(remote_tasks),
            "tasks_imported": 0,
            "tasks_updated": 0,
            "tasks_skipped": 0,
            "errors": [],
            "dry_run": dry_run,
        }

        # Process each remote task
        for remote_task in remote_tasks:
            try:
                sync_result = self._sync_single_task(remote_task, mapper, dry_run)

                if sync_result["action"] == "imported":
                    results["tasks_imported"] += 1
                elif sync_result["action"] == "updated":
                    results["tasks_updated"] += 1
                elif sync_result["action"] == "skipped":
                    results["tasks_skipped"] += 1

                if sync_result.get("error"):
                    results["errors"].append(sync_result["error"])

            except Exception as e:
                error_msg = f"Error syncing task {remote_task.remote_id}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        logger.info(f"Sync completed: {results['tasks_imported']} imported, " f"{results['tasks_updated']} updated, {results['tasks_skipped']} skipped")

        return results

    def _sync_single_task(self, remote_task: RemoteTask, mapper: TaskMapper, dry_run: bool) -> Dict[str, Any]:
        """
        Sync a single remote task.

        Args:
            remote_task: Remote task to sync
            mapper: Task mapper for this system type
            dry_run: If True, don't make actual changes

        Returns:
            Dictionary with sync result details
        """
        # Validate remote task
        if not RemoteTaskValidator.is_valid(remote_task):
            return {"action": "skipped", "reason": "Invalid remote task", "error": f"Validation failed: {RemoteTaskValidator.validate_remote_task(remote_task)}"}

        # Map remote task to local format
        mapping_result = mapper.map_remote_task(remote_task)
        if not mapping_result.success:
            return {"action": "skipped", "reason": "Mapping failed", "error": mapping_result.error_message}

        # Check if task already exists locally
        existing_task_id = self._find_existing_remote_task(remote_task.remote_id, remote_task.remote_source)

        if existing_task_id:
            # Update existing task
            return self._update_existing_task(existing_task_id, remote_task, mapping_result, dry_run)
        else:
            # Import new task
            return self._import_new_task(remote_task, mapping_result, dry_run)

    def _find_existing_remote_task(self, remote_id: str, remote_source: str) -> Optional[int]:
        """
        Find existing local task by remote ID and source.

        Args:
            remote_id: Remote task ID
            remote_source: Remote system source

        Returns:
            Local task ID if found, None otherwise
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM tasks WHERE remote_id = ? AND remote_source = ?", (remote_id, remote_source))
            result = cursor.fetchone()
            return result[0] if result else None

    def _import_new_task(self, remote_task: RemoteTask, mapping_result: TaskMappingResult, dry_run: bool) -> Dict[str, Any]:
        """
        Import a new remote task to local database.

        Args:
            remote_task: Remote task to import
            mapping_result: Result of mapping the remote task
            dry_run: If True, don't make actual changes

        Returns:
            Dictionary with import result details
        """
        if dry_run:
            return {
                "action": "imported",
                "reason": "Dry run - would import new task",
                "task_id": None,
                "content": mapping_result.local_content,
                "labels": mapping_result.local_labels,
            }

        try:
            # Add task to local database
            task_id = self.task_manager.add_task(content=mapping_result.local_content, labels=",".join(mapping_result.local_labels) if mapping_result.local_labels else None, source="remote_sync", due_date=None, context="default")

            # Update task with remote tracking information
            self._update_task_remote_info(task_id, remote_task.remote_id, remote_task.remote_source, remote_task.authority.value, remote_task.is_shadow_task, remote_task.remote_status, datetime.now())

            return {
                "action": "imported",
                "reason": "New task imported",
                "task_id": task_id,
                "content": mapping_result.local_content,
                "labels": mapping_result.local_labels,
            }

        except Exception as e:
            return {"action": "skipped", "reason": "Import failed", "error": str(e)}

    def _update_existing_task(self, task_id: int, remote_task: RemoteTask, mapping_result: TaskMappingResult, dry_run: bool) -> Dict[str, Any]:
        """
        Update an existing local task with remote information.

        Args:
            task_id: Local task ID to update
            remote_task: Remote task data
            mapping_result: Result of mapping the remote task
            dry_run: If True, don't make actual changes

        Returns:
            Dictionary with update result details
        """
        if dry_run:
            return {
                "action": "updated",
                "reason": "Dry run - would update existing task",
                "task_id": task_id,
                "content": mapping_result.local_content,
            }

        try:
            # Update task content and labels if needed
            # For now, we'll just update the remote tracking info
            # In the future, we might want to sync content for status-only authority tasks

            self._update_task_remote_info(task_id, remote_task.remote_id, remote_task.remote_source, remote_task.authority.value, remote_task.is_shadow_task, remote_task.remote_status, datetime.now())

            return {
                "action": "updated",
                "reason": "Existing task updated",
                "task_id": task_id,
                "content": mapping_result.local_content,
            }

        except Exception as e:
            return {"action": "skipped", "reason": "Update failed", "error": str(e)}

    def _update_task_remote_info(
        self,
        task_id: int,
        remote_id: str,
        remote_source: str,
        remote_authority: str,
        is_shadow_task: bool,
        remote_status: Optional[str],
        last_synced_at: datetime,
    ):
        """
        Update remote tracking information for a local task.

        Args:
            task_id: Local task ID
            remote_id: Remote task ID
            remote_source: Remote system source
            remote_authority: Authority type (full/status_only)
            is_shadow_task: Whether this is a shadow task
            remote_status: Remote status (for status-only authority)
            last_synced_at: When the task was last synced
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE tasks 
                SET remote_id = ?, remote_source = ?, remote_authority = ?, 
                    is_shadow_task = ?, remote_status = ?, last_synced_at = ?
                WHERE id = ?
                """,
                (remote_id, remote_source, remote_authority, is_shadow_task, remote_status, last_synced_at, task_id),
            )
            conn.commit()

    def get_sync_status(self, remote_source: Optional[str] = None) -> Dict[str, Any]:
        """
        Get synchronization status for tasks.

        Args:
            remote_source: Optional filter by remote source

        Returns:
            Dictionary with sync status information
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            if remote_source:
                cursor.execute(
                    """
                    SELECT remote_authority, is_shadow_task, COUNT(*) as count
                    FROM tasks 
                    WHERE remote_source = ? AND remote_id IS NOT NULL
                    GROUP BY remote_authority, is_shadow_task
                    """,
                    (remote_source,),
                )
            else:
                cursor.execute(
                    """
                    SELECT remote_authority, is_shadow_task, COUNT(*) as count
                    FROM tasks 
                    WHERE remote_id IS NOT NULL
                    GROUP BY remote_authority, is_shadow_task
                    """
                )

            results = cursor.fetchall()

            # Get total counts
            if remote_source:
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE remote_id IS NOT NULL AND remote_source = ?", (remote_source,))
                total_remote_tasks = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM tasks WHERE remote_source = ?", (remote_source,))
                total_tasks = cursor.fetchone()[0]
            else:
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE remote_id IS NOT NULL")
                total_remote_tasks = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM tasks")
                total_tasks = cursor.fetchone()[0]

            # Format results
            status = {"total_tasks": total_tasks, "total_remote_tasks": total_remote_tasks, "remote_tasks_by_authority": {}, "last_sync_info": {}}

            for authority, is_shadow, count in results:
                key = f"{authority}_{is_shadow}"
                status["remote_tasks_by_authority"][key] = count

            # Get last sync information
            if remote_source:
                cursor.execute(
                    """
                    SELECT MAX(last_synced_at) as last_sync
                    FROM tasks 
                    WHERE remote_source = ? AND last_synced_at IS NOT NULL
                    """,
                    (remote_source,),
                )
            else:
                cursor.execute(
                    """
                    SELECT MAX(last_synced_at) as last_sync
                    FROM tasks 
                    WHERE last_synced_at IS NOT NULL
                    """
                )

            last_sync_result = cursor.fetchone()
            if last_sync_result and last_sync_result[0]:
                status["last_sync_info"]["last_sync"] = last_sync_result[0]

            return status

    def cleanup_remote_tasks(self, remote_source: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up remote tasks that are no longer needed.

        This is typically used for full authority tasks that have been imported
        and should be removed from the remote system.

        Args:
            remote_source: Remote system source to clean up
            dry_run: If True, don't make actual changes

        Returns:
            Dictionary with cleanup results
        """
        logger.info(f"Starting cleanup for remote source: {remote_source}")

        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")

        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Find tasks that are ready for cleanup
            cursor.execute(
                """
                SELECT id, remote_id, content, remote_authority
                FROM tasks 
                WHERE remote_source = ? 
                AND remote_authority = 'full'
                AND last_synced_at IS NOT NULL
                """,
                (remote_source,),
            )

            tasks_to_cleanup = cursor.fetchall()

            results = {
                "total_tasks": len(tasks_to_cleanup),
                "tasks_cleaned": 0,
                "errors": [],
                "dry_run": dry_run,
            }

            for task_id, remote_id, content, authority in tasks_to_cleanup:
                try:
                    if not dry_run:
                        # Mark task as cleaned up
                        cursor.execute("UPDATE tasks SET last_synced_at = ? WHERE id = ?", (datetime.now(), task_id))

                    results["tasks_cleaned"] += 1
                    logger.debug(f"Cleaned up task {task_id} (remote_id: {remote_id})")

                except Exception as e:
                    error_msg = f"Error cleaning up task {task_id}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            if not dry_run:
                conn.commit()

            logger.info(f"Cleanup completed: {results['tasks_cleaned']} tasks cleaned")
            return results
