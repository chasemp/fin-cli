# Database Pollution Prevention Guide

## 🚨 **CRITICAL ISSUE RESOLVED**

**Problem**: Tests were polluting the user's personal task database (`~/fin/tasks.db`) with test data.

**Root Cause**: CLI functions were calling `DatabaseManager()` directly instead of using the `_get_db_manager()` function that respects the `FIN_DB_PATH` environment variable.

**Solution**: All CLI functions now use `_get_db_manager()` which properly checks for test isolation.

## ✅ **CURRENT STATUS: FIXED**

- **All CLI functions** now use `_get_db_manager()` 
- **Test isolation** is properly enforced via `FIN_DB_PATH` environment variable
- **Global fixture** `isolate_tests_from_real_database` runs automatically for all tests
- **No more database pollution** from tests

## 🔧 **How Test Isolation Works**

### **1. Global Test Fixture (conftest.py)**
```python
@pytest.fixture(autouse=True)
def isolate_tests_from_real_database(monkeypatch):
    """Global fixture that ensures all tests use isolated databases."""
    # Create a temporary database path for this test
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db_path = tmp.name

    # Set the environment variable to use the temp database
    monkeypatch.setenv("FIN_DB_PATH", temp_db_path)
    
    yield
    
    # Clean up the temporary database
    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)
```

**This fixture runs automatically for every test** and ensures:
- `FIN_DB_PATH` is always set to a temporary location
- Tests can never accidentally access the real database
- Temporary databases are automatically cleaned up

### **2. Database Manager Function (cli.py)**
```python
def _get_db_manager():
    """Get database manager - lazy initialization to avoid import-time connections."""
    # Check for environment variable first to ensure proper test isolation
    env_db_path = os.environ.get("FIN_DB_PATH")
    if env_db_path:
        return DatabaseManager(env_db_path)  # Use test database
    else:
        return DatabaseManager()  # Use default location
```

**All CLI functions must use this function** instead of calling `DatabaseManager()` directly.

## 🚫 **NEVER DO THIS (Database Pollution)**

```python
# ❌ WRONG - Direct instantiation (POLLUTES REAL DATABASE)
def some_function():
    db_manager = DatabaseManager()  # NEVER do this in CLI functions
    
# ❌ WRONG - Module-level instantiation (POLLUTES ON IMPORT)
db_manager = DatabaseManager()  # NEVER at module level
```

## ✅ **ALWAYS DO THIS (Proper Test Isolation)**

```python
# ✅ CORRECT - Use the safe function
def some_function():
    db_manager = _get_db_manager()  # Always use this in CLI functions
    
# ✅ CORRECT - Dependency injection
def some_function(db_manager: DatabaseManager):
    # Use provided db_manager (tests provide isolated instances)
    
# ✅ CORRECT - Environment variable check
def some_function():
    env_db_path = os.environ.get("FIN_DB_PATH")
    if env_db_path:
        db_manager = DatabaseManager(env_db_path)  # Test database
    else:
        db_manager = DatabaseManager()  # Real database
```

## 🧪 **Testing Best Practices**

### **1. Use Test Fixtures**
```python
def test_something(temp_db_path, monkeypatch):
    """Test with proper isolation."""
    # Environment is automatically set by global fixture
    # Just use the database manager normally
    db_manager = DatabaseManager()  # Will use FIN_DB_PATH automatically
    
    # Your test logic here
    task_manager = TaskManager(db_manager)
    task_id = task_manager.add_task("Test task")
    
    # Verify results
    task = task_manager.get_task(task_id)
    assert task["content"] == "Test task"
```

### **2. Test Real Database Behavior (When Needed)**
```python
def test_real_database_creation(monkeypatch, allow_real_database):
    """Test actual database creation logic."""
    # This fixture removes FIN_DB_PATH to test real behavior
    with tempfile.TemporaryDirectory() as tmp_home:
        monkeypatch.setenv("HOME", tmp_home)
        
        # Now DatabaseManager() will create real database
        db_manager = DatabaseManager()  # This is OK in this context
        
        # Test real database creation
        fin_dir = Path(tmp_home) / "fin"
        assert fin_dir.exists()
```

### **3. Verify Test Isolation**
```python
def test_isolation_working(temp_db_path, monkeypatch):
    """Verify that test isolation is working."""
    # Check environment variable
    assert os.environ.get("FIN_DB_PATH") == temp_db_path
    
    # Check database path
    db_manager = DatabaseManager()
    assert db_manager.db_path == temp_db_path
    
    # Verify it's not the real database
    real_db_path = os.path.expanduser("~/fin/tasks.db")
    assert db_manager.db_path != real_db_path
```

## 🔍 **How to Detect Database Pollution**

### **1. Check for Test Data in Real Database**
```bash
# Look for test task content
fin list | grep -i "test\|example\|sample"

# Check for tasks with test labels
fin list -l "test"
fin list -l "example"
fin list -l "sample"
```

### **2. Check Database File Modification Times**
```bash
# Check when database was last modified
ls -la ~/fin/tasks.db

# Check if database was modified during test run
stat ~/fin/tasks.db
```

### **3. Monitor Database During Tests**
```bash
# Watch database file during test run
watch -n 1 'ls -la ~/fin/tasks.db'

# Check for database connections
lsof | grep tasks.db
```

## 🛠️ **Debugging Database Pollution**

### **1. Check Environment Variables**
```python
import os
print(f"FIN_DB_PATH: {os.environ.get('FIN_DB_PATH')}")
print(f"Current working directory: {os.getcwd()}")
```

### **2. Check Database Path Resolution**
```python
from fincli.db import DatabaseManager
db_manager = DatabaseManager()
print(f"Database path: {db_manager.db_path}")
print(f"Real database path: {os.path.expanduser('~/fin/tasks.db')}")
print(f"Using test database: {db_manager.db_path != os.path.expanduser('~/fin/tasks.db')}")
```

### **3. Add Debug Logging**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

def _get_db_manager():
    env_db_path = os.environ.get("FIN_DB_PATH")
    print(f"DEBUG: FIN_DB_PATH = {env_db_path}")
    
    if env_db_path:
        print(f"DEBUG: Using test database: {env_db_path}")
        return DatabaseManager(env_db_path)
    else:
        print(f"DEBUG: Using real database (default)")
        return DatabaseManager()
```

## 📋 **Prevention Checklist**

### **Before Committing Code**
- [ ] No direct `DatabaseManager()` calls in CLI functions
- [ ] All CLI functions use `_get_db_manager()`
- [ ] No module-level database operations
- [ ] Tests use proper fixtures for database isolation

### **Before Running Tests**
- [ ] `FIN_DB_PATH` environment variable is set (automatic via fixture)
- [ ] No real database connections active
- [ ] Test environment properly isolated

### **After Running Tests**
- [ ] All tests pass
- [ ] No test data in real database
- [ ] No temporary files left behind
- [ ] Real database unchanged

## 🚨 **Emergency Response**

### **If Database Pollution is Detected**

1. **Immediate Action**
   ```bash
   # Stop all tests immediately
   pkill -f pytest
   
   # Check what was polluted
   fin list | grep -i "test\|example"
   ```

2. **Clean Up**
   ```bash
   # Remove test tasks (be careful!)
   fin list | grep -i "test" | awk '{print $2}' | xargs -I {} fin delete {}
   
   # Or restore from backup if available
   fin backup restore latest
   ```

3. **Investigate Root Cause**
   - Check for direct `DatabaseManager()` calls
   - Verify environment variable handling
   - Check test isolation fixtures

4. **Prevent Future Occurrences**
   - Add database pollution detection to CI/CD
   - Implement automated testing for isolation
   - Add code review requirements

## 📊 **Monitoring and Validation**

### **1. Automated Checks**
```bash
# Check for direct DatabaseManager calls
grep -r "DatabaseManager()" fincli/ --exclude-dir=__pycache__

# Check for proper usage
grep -r "_get_db_manager()" fincli/ --exclude-dir=__pycache__
```

### **2. Test Isolation Validation**
```bash
# Run tests with database monitoring
FIN_DB_PATH=/tmp/monitor.db python -m pytest tests/ -v

# Check if real database was accessed
ls -la ~/fin/tasks.db*
```

### **3. Continuous Integration**
- Add database pollution detection to CI pipeline
- Run tests with explicit environment variables
- Validate test isolation on every commit

## 🎯 **Success Metrics**

- **Zero database pollution incidents**
- **100% test isolation reliability**
- **All tests use proper fixtures**
- **No direct DatabaseManager() calls in CLI functions**
- **Environment variables properly respected**

## 📚 **Related Documentation**

- [TESTING.md](TESTING.md) - General testing guidelines
- [DATABASE_OPERATIONS_GUIDE.md](DATABASE_OPERATIONS_GUIDE.md) - Database operation patterns
- [DATABASE_TROUBLESHOOTING.md](DATABASE_TROUBLESHOOTING.md) - Troubleshooting guide

---

**Remember**: Test isolation is non-negotiable. Never let tests pollute real user data!
