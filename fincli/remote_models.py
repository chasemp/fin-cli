"""
Remote task models and authority definitions for FinCLI.

Defines the data structures and enums for handling different types of remote task systems.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskAuthority(Enum):
    """Defines the authority level for remote tasks."""

    FULL_AUTHORITY = "full"
    """Local system is authoritative for both task definition and status."""

    STATUS_ONLY_AUTHORITY = "status_only"
    """Local system is only authoritative for status, remote is authoritative for definition."""


class RemoteSystemType(Enum):
    """Defines the type of remote system."""

    GOOGLE_SHEETS = "google_sheets"
    """Google Sheets - typically full authority, purge after import."""

    CONFLUENCE = "confluence"
    """Confluence - typically status authority only."""

    JIRA = "jira"
    """Jira - typically status authority only."""

    SLACK = "slack"
    """Slack - typically full authority, purge after import."""

    EMAIL = "email"
    """Email - typically full authority, purge after import."""


@dataclass
class RemoteTask:
    """Represents a task from a remote system."""

    # Core task data
    remote_id: str
    remote_source: str
    content: str
    labels: Optional[List[str]] = None

    # Authority and sync information
    authority: TaskAuthority = TaskAuthority.FULL_AUTHORITY
    is_shadow_task: bool = False

    # Remote metadata
    remote_created_at: Optional[datetime] = None
    remote_updated_at: Optional[datetime] = None
    remote_status: Optional[str] = None

    # Local sync tracking
    local_task_id: Optional[int] = None
    last_synced_at: Optional[datetime] = None
    sync_status: str = "pending"  # pending, synced, failed

    # Additional remote fields (system-specific)
    remote_metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate the remote task data."""
        if not self.remote_id:
            raise ValueError("remote_id is required")
        if not self.remote_source:
            raise ValueError("remote_source is required")
        if not self.content:
            raise ValueError("content is required")

        # Set is_shadow_task based on authority
        if self.authority == TaskAuthority.STATUS_ONLY_AUTHORITY:
            self.is_shadow_task = True


@dataclass
class TaskMappingResult:
    """Result of mapping a remote task to local format."""

    success: bool
    local_content: str
    local_labels: List[str]
    error_message: Optional[str] = None

    # Authority-specific information
    should_purge_remote: bool = False
    should_update_remote_status: bool = False


class TaskMapper:
    """Maps remote tasks to local task format based on authority type."""

    def __init__(self, system_type: RemoteSystemType):
        """
        Initialize the task mapper.

        Args:
            system_type: Type of remote system being mapped
        """
        self.system_type = system_type
        self.default_authority = self._get_default_authority()

    def _get_default_authority(self) -> TaskAuthority:
        """Get the default authority for this system type."""
        if self.system_type in [RemoteSystemType.GOOGLE_SHEETS, RemoteSystemType.SLACK, RemoteSystemType.EMAIL]:
            return TaskAuthority.FULL_AUTHORITY
        elif self.system_type in [RemoteSystemType.CONFLUENCE, RemoteSystemType.JIRA]:
            return TaskAuthority.STATUS_ONLY_AUTHORITY
        else:
            return TaskAuthority.FULL_AUTHORITY

    def map_remote_task(self, remote_task: RemoteTask) -> TaskMappingResult:
        """
        Map a remote task to local task format.

        Args:
            remote_task: Remote task to map

        Returns:
            TaskMappingResult with local content and labels
        """
        try:
            # Set authority based on system type, but respect if already explicitly set
            if not hasattr(remote_task, "_authority_explicitly_set") or not remote_task._authority_explicitly_set:
                remote_task.authority = self.default_authority
            # Note: We can't easily detect if authority was explicitly set in the constructor
            # So we'll always use the system type for now

            # Set shadow task flag based on authority
            remote_task.is_shadow_task = remote_task.authority == TaskAuthority.STATUS_ONLY_AUTHORITY

            # Format local content
            local_content = self._format_local_content(remote_task)

            # Determine local labels
            local_labels = self._determine_local_labels(remote_task)

            # Determine sync behavior
            should_purge_remote = remote_task.authority == TaskAuthority.FULL_AUTHORITY
            should_update_remote_status = remote_task.authority == TaskAuthority.STATUS_ONLY_AUTHORITY

            return TaskMappingResult(success=True, local_content=local_content, local_labels=local_labels, should_purge_remote=should_purge_remote, should_update_remote_status=should_update_remote_status)

        except Exception as e:
            return TaskMappingResult(success=False, local_content="", local_labels=[], error_message=str(e))

    def _format_local_content(self, remote_task: RemoteTask) -> str:
        """Format the local task content."""
        # Always add #remote tag
        content = remote_task.content

        # Add authority-specific tags
        if remote_task.authority == TaskAuthority.STATUS_ONLY_AUTHORITY:
            content += " #shadow"

        content += " #remote"

        return content

    def _determine_local_labels(self, remote_task: RemoteTask) -> List[str]:
        """Determine local labels for the task."""
        labels = []

        # Add system-specific labels
        labels.append(f"source:{remote_task.remote_source}")

        # Add authority labels
        if remote_task.authority == TaskAuthority.FULL_AUTHORITY:
            labels.append("authority:full")
        else:
            labels.append("authority:status")

        # Add custom labels if provided
        if remote_task.labels:
            labels.extend(remote_task.labels)

        return labels


class RemoteTaskValidator:
    """Validates remote task data before processing."""

    @staticmethod
    def validate_remote_task(remote_task: RemoteTask) -> List[str]:
        """
        Validate a remote task and return list of validation errors.

        Args:
            remote_task: Remote task to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Required fields
        if not remote_task.remote_id:
            errors.append("remote_id is required")
        if not remote_task.remote_source:
            errors.append("remote_source is required")
        if not remote_task.content:
            errors.append("content is required")

        # Authority validation
        if remote_task.authority and not isinstance(remote_task.authority, TaskAuthority):
            errors.append(f"Invalid authority: {remote_task.authority}")

        # Content length validation
        if remote_task.content and len(remote_task.content) > 1000:
            errors.append("Content too long (max 1000 characters)")

        # Remote ID format validation
        if remote_task.remote_id and len(remote_task.remote_id) > 100:
            errors.append("Remote ID too long (max 100 characters)")

        return errors

    @staticmethod
    def is_valid(remote_task: RemoteTask) -> bool:
        """Check if a remote task is valid."""
        return len(RemoteTaskValidator.validate_remote_task(remote_task)) == 0


# Factory functions for creating remote tasks from different sources
def create_google_sheets_task(remote_id: str, content: str, user_name: str = "", text: str = "", permalink: str = "", source: str = "google_sheets", **kwargs) -> RemoteTask:
    """Create a Google Sheets remote task."""
    # Format content if individual fields provided
    if not content and (user_name or text or permalink):
        parts = [user_name, text, permalink]
        content = " ".join([part for part in parts if part])

    return RemoteTask(remote_id=remote_id, remote_source=source, content=content, authority=TaskAuthority.FULL_AUTHORITY, is_shadow_task=False, **kwargs)


def create_confluence_task(remote_id: str, content: str, remote_status: str = "open", **kwargs) -> RemoteTask:
    """Create a Confluence remote task."""
    return RemoteTask(remote_id=remote_id, remote_source="confluence", content=content, remote_status=remote_status, authority=TaskAuthority.STATUS_ONLY_AUTHORITY, is_shadow_task=True, **kwargs)
