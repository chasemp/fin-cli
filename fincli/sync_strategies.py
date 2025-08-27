"""
Sync Strategies for FinCLI

Implements specialized synchronization strategies for different remote systems.
"""

from dataclasses import asdict
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple

from .remote_models import (
    RemoteSystemType,
    RemoteTask,
    RemoteTaskValidator,
    TaskAuthority,
    TaskMapper,
    TaskMappingResult,
)
from .sheets_connector import SheetsReader
from .sync_engine import SyncEngine

logger = logging.getLogger(__name__)


class GoogleSheetsSyncStrategy:
    """Specialized sync strategy for Google Sheets."""

    def __init__(self, sync_engine: SyncEngine, sheets_reader: SheetsReader, column_mapping: Dict[str, str] = None):
        """
        Initialize the Google Sheets sync strategy.

        Args:
            sync_engine: Base sync engine instance
            sheets_reader: Google Sheets reader instance
            column_mapping: Optional mapping of expected columns to actual column names
        """
        self.sync_engine = sync_engine
        self.sheets_reader = sheets_reader
        self.system_type = RemoteSystemType.GOOGLE_SHEETS
        self.column_mapping = column_mapping or {}

    def sync_sheet_tasks(self, sheet_name: str = "todo", dry_run: bool = False, purge_after_import: bool = True) -> Dict[str, Any]:
        """
        Sync tasks from a specific Google Sheet.

        Args:
            sheet_name: Name of the sheet to sync from
            dry_run: If True, don't make actual changes
            purge_after_import: Whether to purge remote tasks after import

        Returns:
            Dictionary with sync results
        """
        logger.info(f"Starting Google Sheets sync from sheet: {sheet_name}")

        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")

        try:
            # Read tasks from the sheet
            rows = self.sheets_reader.read_all_rows(sheet_name)
            if not rows:
                logger.info(f"No rows found in sheet '{sheet_name}'")
                return {"success": True, "sheet_name": sheet_name, "total_rows": 0, "tasks_processed": 0, "dry_run": dry_run, "message": "No rows to process"}

            # Parse tasks from rows using column mapping if available
            # First row should be headers, rest are data
            headers = rows[0]
            data_rows = rows[1:]
            remote_tasks = self.sheets_reader.parse_task_data(data_rows, self.column_mapping, headers)
            logger.info(f"Parsed {len(remote_tasks)} tasks from sheet '{sheet_name}'")

            # Sync tasks using the base engine
            sync_results = self.sync_engine.sync_remote_tasks(remote_tasks, self.system_type, dry_run=dry_run)

            # Add sheet-specific information
            sync_results.update({"sheet_name": sheet_name, "total_rows": len(rows), "success": True, "dry_run": dry_run})

            # Handle remote task purging if requested and not dry run
            if purge_after_import and not dry_run and sync_results["tasks_imported"] > 0:
                purge_results = self._purge_remote_tasks(remote_tasks, sheet_name)
                sync_results["purge_results"] = purge_results

            logger.info(f"Google Sheets sync completed for sheet '{sheet_name}': " f"{sync_results['tasks_imported']} imported, " f"{sync_results['tasks_updated']} updated")

            return sync_results

        except Exception as e:
            error_msg = f"Error syncing Google Sheets: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "sheet_name": sheet_name, "error": error_msg, "dry_run": dry_run}

    def _purge_remote_tasks(self, remote_tasks: List[RemoteTask], sheet_name: str) -> Dict[str, Any]:
        """
        Purge remote tasks from Google Sheets after successful import.

        Args:
            remote_tasks: List of remote tasks that were imported
            sheet_name: Name of the sheet to purge from

        Returns:
            Dictionary with purge results
        """
        logger.info(f"Starting purge of {len(remote_tasks)} tasks from sheet '{sheet_name}'")

        purge_results = {"total_tasks": len(remote_tasks), "tasks_purged": 0, "errors": [], "sheet_name": sheet_name}

        # For Google Sheets, we need to delete rows
        # This is a simplified implementation - in practice, you'd want to:
        # 1. Batch delete operations
        # 2. Handle row shifting properly
        # 3. Add proper error handling for API limits

        # Collect row numbers for batch deletion
        row_numbers = []
        for remote_task in remote_tasks:
            row_number = remote_task.remote_metadata.get("row_number")
            if row_number is None:
                logger.warning(f"No row number for task {remote_task.remote_id}")
                continue
            row_numbers.append(row_number)

        if not row_numbers:
            logger.warning("No valid row numbers found for purging")
            return purge_results

        # Use batch deletion for efficiency
        try:
            batch_result = self.sheets_reader.batch_delete_rows(sheet_name, row_numbers)

            if batch_result["success"]:
                purge_results["tasks_purged"] = batch_result["deleted_rows"]
                logger.info(f"Successfully purged {batch_result['deleted_rows']} rows from sheet '{sheet_name}'")
            else:
                purge_results["errors"].extend(batch_result["errors"])
                logger.error(f"Batch purge failed: {batch_result['errors']}")

        except Exception as e:
            error_msg = f"Error during batch purge: {str(e)}"
            logger.error(error_msg)
            purge_results["errors"].append(error_msg)

        logger.info(f"Purge completed: {purge_results['tasks_purged']} tasks purged")
        return purge_results

    def get_sync_status(self, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get sync status for Google Sheets tasks.

        Args:
            sheet_name: Optional filter by specific sheet

        Returns:
            Dictionary with sync status information
        """
        # Get general sync status
        status = self.sync_engine.get_sync_status(remote_source="google_sheets")

        # Add Google Sheets specific information
        status["system_type"] = "google_sheets"
        status["sheet_name"] = sheet_name

        # Get sheet information if available
        try:
            sheet_info = self.sheets_reader.get_sheet_info()
            status["sheet_info"] = {"title": sheet_info.get("title", "Unknown"), "sheets": [s["name"] for s in sheet_info.get("sheets", [])]}
        except Exception as e:
            logger.warning(f"Could not get sheet info: {e}")
            status["sheet_info"] = {"error": str(e)}

        return status

    def validate_sheet_structure(self, sheet_name: str) -> Dict[str, Any]:
        """
        Validate that a sheet has the expected structure for task import.

        Args:
            sheet_name: Name of the sheet to validate

        Returns:
            Dictionary with validation results
        """
        logger.info(f"Validating sheet structure for '{sheet_name}'")

        try:
            # Read all rows to get the actual headers and data
            all_rows = self.sheets_reader.read_all_rows(sheet_name)

            if not all_rows:
                return {"valid": False, "sheet_name": sheet_name, "error": "Sheet is empty or not accessible"}

            # The first row should contain the actual headers
            headers = all_rows[0]
            logger.info(f"Found headers: {headers}")

            # Check if we have the expected headers using column mapping
            if self.column_mapping:
                # Use column mapping to validate headers
                expected_headers = list(self.column_mapping.values())
                missing_headers = [h for h in expected_headers if h not in headers]

                if missing_headers:
                    return {"valid": False, "sheet_name": sheet_name, "missing_headers": missing_headers, "found_headers": headers, "error": f"Missing required headers: {missing_headers}"}
            else:
                # Fallback to default header validation
                headers_lower = [cell.lower().strip() for cell in headers if cell]
                normalized_headers = [h.replace(" ", "_") for h in headers_lower]
                required_headers = ["source", "runid", "user_name", "text"]

                missing_headers = [h for h in required_headers if h not in normalized_headers]

                if missing_headers:
                    return {"valid": False, "sheet_name": sheet_name, "missing_headers": missing_headers, "found_headers": headers, "error": f"Missing required headers: {missing_headers}"}

            # Try to parse a few rows to validate data structure
            try:
                # Only try to parse if we have data rows (not just headers)
                if len(all_rows) > 1:
                    # Use the first few data rows for validation
                    sample_rows = all_rows[1:6]  # Skip header row, take next 5 rows
                    remote_tasks = self.sheets_reader.parse_task_data(sample_rows, self.column_mapping, headers)
                    valid_tasks = [task for task in remote_tasks if RemoteTaskValidator.is_valid(task)]

                    return {"valid": True, "sheet_name": sheet_name, "total_rows": len(all_rows), "sample_rows_parsed": len(sample_rows), "valid_tasks_found": len(valid_tasks), "found_headers": headers}
                else:
                    # Only headers, no data rows
                    return {"valid": False, "sheet_name": sheet_name, "total_rows": len(all_rows), "found_headers": headers, "error": "Sheet contains only headers, no data rows"}

            except Exception as parse_error:
                return {"valid": False, "sheet_name": sheet_name, "found_headers": headers, "parse_error": str(parse_error), "error": f"Failed to parse sample rows: {parse_error}"}

        except Exception as e:
            return {"valid": False, "sheet_name": sheet_name, "error": f"Could not access sheet: {str(e)}"}


class ConfluenceSyncStrategy:
    """Specialized sync strategy for Confluence (placeholder for future implementation)."""

    def __init__(self, sync_engine: SyncEngine):
        """
        Initialize the Confluence sync strategy.

        Args:
            sync_engine: Base sync engine instance
        """
        self.sync_engine = sync_engine
        self.system_type = RemoteSystemType.CONFLUENCE

    def sync_confluence_tasks(self, space_key: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Sync tasks from Confluence (placeholder implementation).

        Args:
            space_key: Confluence space key to sync from
            dry_run: If True, don't make actual changes

        Returns:
            Dictionary with sync results
        """
        logger.info(f"Confluence sync not yet implemented for space: {space_key}")

        return {"success": False, "system_type": "confluence", "space_key": space_key, "error": "Confluence sync not yet implemented", "dry_run": dry_run}


class SyncStrategyFactory:
    """Factory for creating sync strategies based on system type."""

    @staticmethod
    def create_strategy(system_type: RemoteSystemType, sync_engine: SyncEngine, **kwargs):
        """
        Create a sync strategy for the specified system type.

        Args:
            system_type: Type of remote system
            sync_engine: Base sync engine instance
            **kwargs: Additional arguments for specific strategies

        Returns:
            Appropriate sync strategy instance
        """
        if system_type == RemoteSystemType.GOOGLE_SHEETS:
            sheets_reader = kwargs.get("sheets_reader")
            if not sheets_reader:
                raise ValueError("sheets_reader is required for Google Sheets sync strategy")
            column_mapping = kwargs.get("column_mapping")
            return GoogleSheetsSyncStrategy(sync_engine, sheets_reader, column_mapping)

        elif system_type == RemoteSystemType.CONFLUENCE:
            return ConfluenceSyncStrategy(sync_engine)

        else:
            raise ValueError(f"Unsupported system type: {system_type}")


if __name__ == "__main__":
    # Example usage
    print("Sync Strategies Module")
    print("Available strategies:")
    print("- GoogleSheetsSyncStrategy")
    print("- ConfluenceSyncStrategy (placeholder)")
    print("- SyncStrategyFactory")
