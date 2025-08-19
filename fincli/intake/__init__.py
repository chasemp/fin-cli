"""
Intake module for FinCLI

Handles importing tasks from external sources with a plugin architecture.
"""

from typing import Any, Callable, Dict, List, Optional

from ..db import DatabaseManager
from .csv_importer import import_csv_tasks
from .excel_importer import import_excel_tasks
from .json_importer import import_json_tasks
from .sheets_importer import import_sheets_tasks
from .text_importer import import_text_tasks

# Plugin registry for different import sources
SOURCES: Dict[str, Callable] = {
    "csv": import_csv_tasks,
    "json": import_json_tasks,
    "text": import_text_tasks,
    "sheets": import_sheets_tasks,
    "excel": import_excel_tasks,
}


def get_available_sources() -> List[str]:
    """Get list of available import sources."""
    return list(SOURCES.keys())


def import_from_source(source: str, db_manager: DatabaseManager, **kwargs) -> Dict[str, Any]:
    """
    Import tasks from a specific source.

    Args:
        source: Source name (csv, json, text, sheets, excel)
        db_manager: Database manager instance (REQUIRED - prevents database pollution)
        **kwargs: Additional arguments for the importer

    Returns:
        Dictionary with import results
    """
    if source not in SOURCES:
        raise ValueError(f"Unknown source: {source}")

    if db_manager is None:
        raise ValueError("db_manager is required to prevent database pollution during imports")

    importer_func = SOURCES[source]
    return importer_func(db_manager=db_manager, **kwargs)


def import_from_source_with_db(source: str, db_manager, **kwargs) -> Dict[str, Any]:
    """
    Import tasks from a specific source with explicit database manager.

    This function ensures dependency injection is used and prevents
    the importer from creating its own database connection.

    Args:
        source: Source name (csv, json, text, sheets, excel)
        db_manager: Database manager instance (required)
        **kwargs: Additional arguments for the importer

    Returns:
        Dictionary with import results
    """
    if source not in SOURCES:
        raise ValueError(f"Unknown source: {source}")

    importer_func = SOURCES[source]
    return importer_func(db_manager=db_manager, **kwargs)
