"""
Pytest configuration and fixtures for Fin test suite
"""

import os
import tempfile
from datetime import timedelta

import pytest

from fincli.db import DatabaseManager


@pytest.fixture(autouse=True)
def isolate_tests_from_real_database(monkeypatch):
    """
    Global fixture that ensures all tests use isolated databases.

    This fixture runs automatically for every test and prevents tests from
    accidentally using the real user database.
    """
    # Create a temporary database path for this test
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db_path = tmp.name

    # Set the environment variable to use the temp database
    # This ensures tests don't accidentally use the real database
    monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

    # Clean up after the test
    yield

    # Clean up the temporary database
    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)


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
def isolated_cli_runner(temp_db_path, monkeypatch):
    """Create a Click CLI runner with isolated database environment."""
    from click.testing import CliRunner

    # Set up isolated environment for this test
    monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

    runner = CliRunner()

    yield runner

    # Clean up environment variable after test
    monkeypatch.delenv("FIN_DB_PATH", raising=False)


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
    monkeypatch.setattr(
        "fincli.config.Config.get_weekdays_only_lookback",
        mock_get_weekdays_only_lookback,
    )


@pytest.fixture
def allow_real_database(monkeypatch):
    """
    Fixture for tests that intentionally need to test real database behavior.

    This fixture removes the FIN_DB_PATH environment variable and allows
    the test to use the default database location (useful for testing
    the actual database creation logic).
    """
    # Remove the FIN_DB_PATH environment variable to allow real database behavior
    monkeypatch.delenv("FIN_DB_PATH", raising=False)
    yield


@pytest.fixture
def test_dates():
    """Provide consistent test dates for all date-related tests."""
    from datetime import date

    # Use fixed, deterministic dates for consistent testing
    # This ensures our tests are not affected by when they run
    base_date = date(2025, 1, 15)  # Wednesday, January 15, 2025

    return {
        "base": base_date,
        "today": base_date,
        "yesterday": base_date - timedelta(days=1),  # Jan 14
        "last_week": base_date - timedelta(days=7),  # Jan 8
        "last_month": base_date - timedelta(days=30),  # Dec 16, 2024
        "future": base_date + timedelta(days=7),  # Jan 22
        "far_future": base_date + timedelta(days=30),  # Feb 14
        "far_past": base_date - timedelta(days=90),  # Oct 17, 2024
        "old_10_days": base_date - timedelta(days=10),  # Jan 5
    }


@pytest.fixture
def test_datetimes():
    """Provide consistent datetime values for tests."""
    from datetime import datetime

    base_datetime = datetime(2025, 1, 15, 10, 30, 0)  # 10:30 AM

    return {
        "base": base_datetime,
        "morning": base_datetime.replace(hour=9, minute=0),
        "afternoon": base_datetime.replace(hour=14, minute=0),
        "evening": base_datetime.replace(hour=18, minute=0),
        "yesterday": base_datetime - timedelta(days=1),
        "last_week": base_datetime - timedelta(days=7),
    }
