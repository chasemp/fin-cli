# Testing Guide for Fin CLI

## Overview

This document outlines the testing strategy, requirements, and procedures for the Fin CLI project.

## Test Requirements

### Coverage Requirements
- **Minimum Coverage**: 90%
- **Coverage Scope**: All `fincli` modules
- **Coverage Reports**: HTML and terminal output

### Test Categories
- **Unit Tests**: Individual function/class testing
- **Integration Tests**: End-to-end workflow testing
- **CLI Tests**: Command-line interface testing
- **Analytics Tests**: Statistics and reporting testing

## Running Tests

### Basic Test Commands
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_analytics.py

# Run specific test
pytest tests/test_analytics.py::TestAnalyticsManager::test_get_task_counts_empty
```

### Coverage Commands
```bash
# Run tests with coverage
pytest --cov=fincli --cov-report=html

# Check coverage threshold
pytest --cov=fincli --cov-fail-under=90

# Generate coverage report
pytest --cov=fincli --cov-report=term-missing
```

### Test Categories
```bash
# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration

# Run CLI tests only
pytest -m cli

# Run analytics tests only
pytest -m analytics
```

## Test Structure

### Directory Layout
```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_analytics.py        # Analytics functionality tests
├── test_cli.py             # CLI command tests
├── test_database.py        # Database functionality tests
├── test_fine.py            # Editor integration tests
├── test_fins.py            # Task listing tests
├── test_integration.py     # End-to-end workflow tests
└── test_labels.py          # Label management tests
```

### Test Naming Conventions
- **Files**: `test_*.py`
- **Classes**: `Test*`
- **Methods**: `test_*`
- **Descriptive names**: `test_add_task_with_labels`

### Fixtures
- `temp_db_path`: Temporary database path
- `db_manager`: Database manager instance
- `cli_runner`: Click CLI test runner
- `populated_db`: Database with sample data

## Test Categories

### Unit Tests
Test individual functions and classes in isolation.

**Example:**
```python
def test_add_task_basic(self, db_manager):
    """Test adding a basic task without labels."""
    from fincli.tasks import TaskManager
    task_manager = TaskManager(db_manager)
    task_id = task_manager.add_task("Test task")
    
    assert task_id == 1
    task = task_manager.get_task(task_id)
    assert task['content'] == "Test task"
```

### Integration Tests
Test complete workflows and interactions between components.

**Example:**
```python
def test_full_cli_to_database_flow(self, temp_db_path, monkeypatch):
    """Test complete flow from CLI to database storage."""
    monkeypatch.setenv('FIN_DB_PATH', temp_db_path)
    
    # Add task via CLI
    result = subprocess.run([
        sys.executable, '-m', 'fin.cli.main', 'add',
        'Integration test task'
    ], capture_output=True, text=True)
    
    assert result.returncode == 0
```

### CLI Tests
Test command-line interface functionality.

**Example:**
```python
def test_cli_add_task_basic(self, cli_runner):
    """Test basic task addition via CLI."""
    result = cli_runner.invoke(add_task, ['Test task'])
    
    assert result.exit_code == 0
    assert "✅ Task added" in result.output
```

## Test Data Management

### Database Isolation
- Each test uses a temporary database
- Database is cleaned up after each test
- No cross-test contamination

### Sample Data
```python
@pytest.fixture
def sample_tasks():
    """Sample tasks for testing."""
    return [
        {
            'content': 'Write documentation',
            'labels': ['docs', 'work'],
            'source': 'cli'
        },
        # ... more sample tasks
    ]
```

## Pre-commit Hooks

### Installation
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### Hook Configuration
- **pytest**: Runs all tests on commit
- **pytest-cov**: Checks coverage on push
- **flake8**: Code linting
- **black**: Code formatting check
- **isort**: Import sorting check

## CI/CD Integration

### GitHub Actions
```yaml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          pytest tests/ --cov=fincli --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Debugging Tests

### Common Issues

1. **Database Pollution**
   - Ensure tests use temporary databases
   - Check for proper cleanup in fixtures

2. **Import Errors**
   - Verify correct import paths
   - Check for circular imports

3. **Environment Variables**
   - Use `monkeypatch.setenv()` for testing
   - Ensure proper environment isolation

### Debug Commands
```bash
# Run with maximum verbosity
pytest -vvv

# Stop on first failure
pytest -x

# Show local variables on failure
pytest --tb=long

# Run with print statements
pytest -s
```

## Performance Testing

### Test Execution Time
- **Unit tests**: < 1 second each
- **Integration tests**: < 5 seconds each
- **Full suite**: < 30 seconds total

### Memory Usage
- Monitor for memory leaks in database operations
- Clean up resources in fixtures

## Best Practices

### Test Writing
1. **Arrange-Act-Assert**: Structure tests clearly
2. **Descriptive names**: Make test purpose obvious
3. **Single responsibility**: One assertion per test
4. **Isolation**: Tests should not depend on each other

### Test Maintenance
1. **Update tests when changing functionality**
2. **Keep tests simple and readable**
3. **Use meaningful test data**
4. **Document complex test scenarios**

### Coverage Goals
- **Critical paths**: 100% coverage
- **Error handling**: 100% coverage
- **CLI commands**: 100% coverage
- **Overall**: 90% minimum

## Troubleshooting

### Common Problems

1. **Tests failing intermittently**
   - Check for race conditions
   - Ensure proper test isolation
   - Verify cleanup in fixtures

2. **Coverage not meeting threshold**
   - Add tests for uncovered code paths
   - Check for dead code
   - Verify coverage configuration

3. **Slow test execution**
   - Optimize database operations
   - Use appropriate test data size
   - Consider test parallelization

### Getting Help
- Check test logs for detailed error messages
- Review test documentation
- Consult team for complex test scenarios 