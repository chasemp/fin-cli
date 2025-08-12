"""
Pytest configuration and fixtures for Fin test suite
"""

import os
import tempfile

import pytest

from fincli.db import DatabaseManager


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
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
            "content": "Write documentation",
            "labels": ["docs", "work"],
            "source": "cli",
        },
        {
            "content": "Buy groceries",
            "labels": ["personal", "shopping"],
            "source": "cli",
        },
        {
            "content": "Review pull request",
            "labels": ["work", "urgent"],
            "source": "cli",
        },
        {"content": "Call mom", "labels": None, "source": "cli"},
    ]


@pytest.fixture
def populated_db(db_manager, sample_tasks):
    """Create a database populated with sample tasks."""
    from fincli.tasks import TaskManager

    task_manager = TaskManager(db_manager)

    for task in sample_tasks:
        task_manager.add_task(
            content=task["content"],
            labels=task["labels"],
            source=task["source"],
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
        monkeypatch.setenv("HOME", tmp_dir)
        yield tmp_dir


@pytest.fixture
def weekdays_only_disabled(monkeypatch):
    """Disable weekdays-only lookback for tests that expect all-days behavior."""
    # Mock the config to return False for weekdays_only_lookback
    def mock_get_weekdays_only_lookback():
        return False
    
    # Apply the mock to the Config class
    monkeypatch.setattr("fincli.config.Config.get_weekdays_only_lookback", mock_get_weekdays_only_lookback)
