# Testing Guide for FinCLI

## 🚫 **CRITICAL: Never Call the Actual Editor in Tests**

**Tests should NEVER call the actual editor** because:
- Editors are **blocking operations** that hang tests
- Tests should be **fast and reliable**
- We want to test **parsing logic**, not external editor behavior
- External editors can have different behaviors across systems

## ✅ **Correct Testing Approach**

### **For Editor Functionality:**
1. **Use `create_edit_file_content()`** to generate initial text
2. **Manipulate the text** to simulate user edits
3. **Use `parse_edited_content()`** to test parsing logic
4. **Verify the results** match expected changes

### **Example:**
```python
def test_task_completion_parsing(temp_db_path):
    """Test that completed tasks are correctly parsed."""
    # Setup database and tasks
    db_manager = DatabaseManager(temp_db_path)
    editor_manager = EditorManager(db_manager)
    
    # Create original content
    tasks = editor_manager.get_tasks_for_editing(label="work")
    original_content = editor_manager.create_edit_file_content(tasks)
    
    # Simulate user editing (mark task as completed)
    edited_content = original_content.replace("[ ]", "[x]", 1)
    
    # Test the parsing logic - now returns 5 values
    completed_count, reopened_count, new_tasks_count, content_modified_count, deleted_count = (
        editor_manager.parse_edited_content(edited_content)
    )
    
    # Verify results
    assert completed_count == 1
    assert reopened_count == 0
    assert content_modified_count == 0
```

## 🔧 **Test Database Isolation**

All tests use **isolated, temporary databases** via the `temp_db_path` fixture:

```python
def test_something(temp_db_path, monkeypatch):
    # Set environment to use temp database
    monkeypatch.setenv("FIN_DB_PATH", temp_db_path)
    
    # Your test logic here
    db_manager = DatabaseManager(temp_db_path)
```

### **Global Test Isolation**

The test suite automatically isolates all tests from your personal database:

- **`isolate_tests_from_real_database`** (autouse=True): Sets `FIN_DB_PATH` to a temporary location
- **`temp_db_path`**: Provides a unique temporary database path for each test
- **`allow_real_database`**: Optional fixture to override isolation for specific tests

## 📋 **Test Categories**

### **1. Unit Tests**
- Test individual functions in isolation
- Mock external dependencies
- Fast execution

### **2. Integration Tests**
- Test component interactions
- Use temporary databases
- Verify data flow

### **3. Editor Tests**
- Test parsing logic with text files
- Simulate user edits
- Verify change detection

## 🚨 **What NOT to Do**

```python
# ❌ WRONG - Never call the actual editor
def test_editor():
    editor_manager.edit_tasks()  # This opens a real editor!

# ❌ WRONG - Don't mock subprocess.run to fake editor
def test_editor():
    monkeypatch.setattr("subprocess.run", mock_editor)
    editor_manager.edit_tasks()

# ❌ WRONG - Don't test external editor behavior
def test_editor():
    result = subprocess.run(["vim", "file.txt"])  # Real editor!
```

## ✅ **What TO Do**

```python
# ✅ CORRECT - Test parsing logic with text files
def test_editor():
    original = editor_manager.create_edit_file_content(tasks)
    edited = simulate_user_edits(original)
    changes = editor_manager.parse_edited_content(edited)
    assert changes.completed_count == 1

# ✅ CORRECT - Test internal state and logic
def test_safety():
    assert not editor_manager._editor_opened
    editor_manager._editor_opened = True
    with pytest.raises(RuntimeError):
        editor_manager.edit_tasks()  # Should raise RuntimeError
```

## 🎯 **Testing Goals**

1. **Fast execution** - Tests should run in seconds, not minutes
2. **Reliable results** - No external dependencies or blocking operations
3. **Logic coverage** - Test the actual parsing and business logic
4. **Isolation** - Each test is independent and uses clean data
5. **Maintainability** - Tests are easy to understand and modify

## 📚 **Key Testing Files**

- `tests/conftest.py` - Global fixtures and test isolation
- `tests/test_editor_safe.py` - Safe editor testing examples
- `tests/test_fine.py` - Fine command testing (updated approach)
- `tests/test_integration.py` - Integration testing patterns

## 🔍 **Running Tests**

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_editor_safe.py -v

# Run with verbose output
python -m pytest tests/ -v -s

# Run with coverage
python -m pytest tests/ --cov=fincli
```

## 🚀 **Best Practices**

1. **Always use `temp_db_path`** for database tests
2. **Test parsing logic**, not external behavior
3. **Use descriptive test names** that explain the scenario
4. **Keep tests focused** on a single piece of functionality
5. **Clean up resources** in fixtures
6. **Document complex test scenarios** with clear comments

## 📝 **Current Return Values**

The `parse_edited_content()` method now returns **5 values**:

```python
# Old (4 values) - DEPRECATED
completed_count, reopened_count, new_tasks_count, deleted_count = (
    editor_manager.parse_edited_content(content)
)

# New (5 values) - CURRENT
completed_count, reopened_count, new_tasks_count, content_modified_count, deleted_count = (
    editor_manager.parse_edited_content(content)
)
```

**Return Value Breakdown:**
- `completed_count`: Number of tasks marked as completed
- `reopened_count`: Number of tasks reopened (unmarked as completed)
- `new_tasks_count`: Number of new tasks added
- `content_modified_count`: Number of tasks with content changes
- `deleted_count`: Number of tasks deleted

## 🔒 **Test Database Schema**

Tests use the current database schema including:

- `id`: Task identifier
- `content`: Task description
- `created_at`: Creation timestamp
- `modified_at`: Last modification timestamp
- `completed_at`: Completion timestamp (NULL if open)
- `labels`: Comma-separated label string
- `source`: Task source (cli, fins, etc.)

**Important:** When testing database operations, account for the `modified_at` column in column mappings.

## 🧪 **Test Data Setup**

When setting up test data:

```python
# ✅ CORRECT - Use task_manager.add_task()
task_id = task_manager.add_task("Test task", labels=["test"])

# ✅ CORRECT - Update completion status
task_manager.update_task_completion(task_id, True)

# ✅ CORRECT - Update task content
task_manager.update_task_content(task_id, "Updated content")
```

## 📅 **Date Handling in Tests - CRITICAL**

**🚫 NEVER use relative dates that depend on when tests run!** This creates non-deterministic, flaky tests.

### **❌ ANTI-PATTERNS (What NOT to do):**

```python
# ❌ WRONG - Non-deterministic relative dates
today = date.today()
yesterday = today - timedelta(days=1)
old_task_date = yesterday - timedelta(days=10)  # What date is this actually?

# ❌ WRONG - Hardcoded relative dates without context
"created_at": f"{yesterday - timedelta(days=30)} 10:00:00"  # When is this?

# ❌ WRONG - Complex date arithmetic that's hard to reason about
task_date = date.today() - timedelta(days=7) + timedelta(hours=2)
```

### **✅ CORRECT PATTERNS (What TO do):**

#### **1. Use Fixed, Deterministic Dates**
```python
# ✅ CORRECT - Fixed, known dates
from datetime import date

# Use specific dates that are easy to reason about
base_date = date(2025, 1, 15)  # January 15, 2025
yesterday_date = date(2025, 1, 14)
old_date = date(2024, 12, 20)

tasks = [
    {
        "id": 1,
        "content": "Old task",
        "created_at": f"{old_date} 10:00:00",
        "completed_at": None,
        "labels": [],
        "source": "cli",
    },
    {
        "id": 2,
        "content": "Recent task", 
        "created_at": f"{yesterday_date} 10:00:00",
        "completed_at": None,
        "labels": [],
        "source": "cli",
    }
]
```

#### **2. Use Date Constants for Common Scenarios**
```python
# ✅ CORRECT - Define date constants at module level
from datetime import date

# Test date constants - easy to understand and modify
TEST_BASE_DATE = date(2025, 1, 15)
TEST_YESTERDAY = date(2025, 1, 14)
TEST_LAST_WEEK = date(2025, 1, 8)
TEST_LAST_MONTH = date(2024, 12, 15)

def test_date_filtering():
    """Test date filtering with known dates."""
    tasks = [
        {
            "id": 1,
            "content": "Old task",
            "created_at": f"{TEST_LAST_MONTH} 10:00:00",
            "completed_at": None,
            "labels": [],
            "source": "cli",
        }
    ]
    # Test logic here...
```

#### **3. Use Relative Dates Only When Testing Relative Logic**
```python
# ✅ CORRECT - Only use relative dates when testing relative date logic
def test_relative_date_filtering():
    """Test that relative date filtering works correctly."""
    from fincli.utils import get_date_range
    
    # This is OK because we're testing the relative date logic itself
    today, lookback = get_date_range(days=7, weekdays_only=False)
    
    # Verify the logic works correctly
    assert lookback == today - timedelta(days=7)
```

#### **4. Use Date Fixtures for Complex Scenarios**
```python
# ✅ CORRECT - Create date fixtures for complex test scenarios
@pytest.fixture
def test_dates():
    """Provide consistent test dates for date-related tests."""
    base_date = date(2025, 1, 15)
    return {
        "base": base_date,
        "yesterday": base_date - timedelta(days=1),
        "last_week": base_date - timedelta(days=7),
        "last_month": base_date - timedelta(days=30),
        "future": base_date + timedelta(days=7),
    }

def test_complex_date_scenarios(test_dates):
    """Test complex date scenarios with consistent dates."""
    tasks = [
        {
            "id": 1,
            "content": "Past task",
            "created_at": f"{test_dates['last_month']} 10:00:00",
            "completed_at": None,
            "labels": [],
            "source": "cli",
        },
        {
            "id": 2, 
            "content": "Future task",
            "created_at": f"{test_dates['future']} 10:00:00",
            "completed_at": None,
            "labels": [],
            "source": "cli",
        }
    ]
    # Test logic here...
```

### **🔍 **Why This Matters:**

1. **Deterministic Tests**: Tests produce the same results regardless of when they run
2. **Easy Debugging**: When tests fail, you know exactly what the date values are
3. **Clear Intent**: Test code clearly shows what dates are being tested
4. **Maintainable**: Easy to modify test dates without complex calculations
5. **Reliable**: No more flaky tests that pass on some days and fail on others

### **📋 **Date Testing Checklist:**

- [ ] **Use fixed, known dates** instead of relative calculations
- [ ] **Define date constants** at module or fixture level
- [ ] **Avoid `date.today()`** in test data setup
- [ ] **Use descriptive date names** (e.g., `TEST_OLD_DATE`, not `old_date`)
- [ ] **Test relative date logic separately** from test data setup
- [ ] **Document date assumptions** in test docstrings

### **🔄 **Migrating Existing Tests:**

If you find existing tests using the anti-pattern, here's how to fix them:

#### **Before (Anti-pattern):**
```python
def test_old_task_filtering():
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    tasks = [
        {
            "id": 1,
            "content": "Old task",
            "created_at": f"{yesterday - timedelta(days=10)} 10:00:00",  # ❌ Unclear date
            "completed_at": None,
            "labels": [],
            "source": "cli",
        }
    ]
    # Test logic...
```

#### **After (Correct pattern):**
```python
# Define test dates at module level
TEST_BASE_DATE = date(2025, 1, 15)
TEST_OLD_DATE = date(2025, 1, 5)  # 10 days before base date

def test_old_task_filtering():
    """Test filtering of tasks older than 10 days."""
    tasks = [
        {
            "id": 1,
            "content": "Old task",
            "created_at": f"{TEST_OLD_DATE} 10:00:00",  # ✅ Clear, known date
            "completed_at": None,
            "labels": [],
            "source": "cli",
        }
    ]
    # Test logic...
```

### **🔍 **Finding Anti-patterns:**

Search your test files for these patterns that need fixing:

```bash
# Search for relative date calculations in tests
grep -r "timedelta.*days" tests/
grep -r "date.today()" tests/
grep -r "yesterday.*timedelta" tests/

# Look for hardcoded relative dates
grep -r "timedelta(days=30)" tests/
grep -r "timedelta(days=7)" tests/
```

### **🏗️ **Creating Reusable Date Fixtures:**

Add this to your `tests/conftest.py` for consistent date handling across all tests:

```python
@pytest.fixture
def test_dates():
    """Provide consistent test dates for all date-related tests."""
    from datetime import date
    
    # Base date - easy to reason about and modify
    base_date = date(2025, 1, 15)  # Wednesday, January 15, 2025
    
    return {
        "base": base_date,
        "yesterday": base_date - timedelta(days=1),      # Jan 14
        "last_week": base_date - timedelta(days=7),     # Jan 8
        "last_month": base_date - timedelta(days=30),   # Dec 16, 2024
        "future": base_date + timedelta(days=7),        # Jan 22
        "far_future": base_date + timedelta(days=30),   # Feb 14
        "far_past": base_date - timedelta(days=90),     # Oct 17, 2024
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
```

**Usage in tests:**
```python
def test_task_date_filtering(test_dates):
    """Test filtering tasks by various date ranges."""
    tasks = [
        {
            "id": 1,
            "content": "Old task",
            "created_at": f"{test_dates['last_month']} 10:00:00",
            "completed_at": None,
            "labels": [],
            "source": "cli",
        },
        {
            "id": 2,
            "content": "Recent task", 
            "created_at": f"{test_dates['yesterday']} 10:00:00",
            "completed_at": None,
            "labels": [],
            "source": "cli",
        },
        {
            "id": 3,
            "content": "Future task",
            "created_at": f"{test_dates['future']} 10:00:00",
            "completed_at": None,
            "labels": [],
            "source": "cli",
        }
    ]
    
    # Test filtering logic with known, predictable dates
    # ...
```

## 🚨 **Common Test Issues**

1. **Column mapping mismatches**: Ensure test column mappings include `modified_at`
2. **Return value count**: Always expect 5 values from `parse_edited_content`
3. **Database isolation**: Never use real database paths in tests
4. **Editor calls**: Never call actual editor methods in tests
5. **Date-related anti-patterns**: Never use relative dates that depend on when tests run

Remember: **Tests should be fast, reliable, and focused on logic, not external interactions!** 