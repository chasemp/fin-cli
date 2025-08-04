"""
Pytest configuration and fixtures for Fin test suite
"""
import pytest
import tempfile
import sqlite3
import os
from pathlib import Path
from fin.database.manager import DatabaseManager


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        return tmp.name


@pytest.fixture
def db_manager(temp_db_path):
    """Create a database manager with a temporary database."""
    manager = DatabaseManager(temp_db_path)
    yield manager
    # Cleanup
    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)


@pytest.fixture
def sample_tasks():
    """Sample tasks for testing."""
    return [
        {
            'content': 'Write documentation',
            'labels': ['docs', 'work'],
            'source': 'cli'
        },
        {
            'content': 'Buy groceries',
            'labels': ['personal', 'shopping'],
            'source': 'cli'
        },
        {
            'content': 'Review pull request',
            'labels': ['work', 'urgent'],
            'source': 'cli'
        },
        {
            'content': 'Call mom',
            'labels': None,
            'source': 'cli'
        }
    ]


@pytest.fixture
def populated_db(db_manager, sample_tasks):
    """Create a database populated with sample tasks."""
    for task in sample_tasks:
        db_manager.add_task(
            content=task['content'],
            labels=task['labels'],
            source=task['source']
        )
    return db_manager


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner for testing."""
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def mock_home_dir(monkeypatch):
    """Mock home directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        monkeypatch.setenv('HOME', tmp_dir)
        yield tmp_dir 