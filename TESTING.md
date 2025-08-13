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

## 🚨 **Common Test Issues**

1. **Column mapping mismatches**: Ensure test column mappings include `modified_at`
2. **Return value count**: Always expect 5 values from `parse_edited_content`
3. **Database isolation**: Never use real database paths in tests
4. **Editor calls**: Never call actual editor methods in tests

Remember: **Tests should be fast, reliable, and focused on logic, not external interactions!** 