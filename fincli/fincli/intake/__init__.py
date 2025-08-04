"""
Intake module for FinCLI

Handles importing tasks from external sources with a plugin architecture.
"""
from typing import Dict, Callable, List, Any
from .csv_importer import import_csv_tasks
from .json_importer import import_json_tasks
from .text_importer import import_text_tasks
from .sheets_importer import import_sheets_tasks
from .excel_importer import import_excel_tasks


# Plugin registry for different import sources
SOURCES: Dict[str, Callable] = {
    'csv': import_csv_tasks,
    'json': import_json_tasks,
    'text': import_text_tasks,
    'sheets': import_sheets_tasks,
    'excel': import_excel_tasks,
}


def get_available_sources() -> List[str]:
    """Get list of available import sources."""
    return list(SOURCES.keys())


def import_from_source(source: str, **kwargs) -> Dict[str, Any]:
    """
    Import tasks from a specific source.
    
    Args:
        source: Source name (csv, json, text, sheets, excel)
        **kwargs: Additional arguments for the importer
        
    Returns:
        Dictionary with import results
    """
    if source not in SOURCES:
        raise ValueError(f"Unknown source: {source}")
    
    return SOURCES[source](**kwargs) 