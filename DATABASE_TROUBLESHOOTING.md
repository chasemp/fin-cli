# Database Troubleshooting Guide for FinCLI

## 🚨 **Common Issues and Solutions**

### **Issue 1: Tests Hanging or Taking Too Long**

**Symptoms:**
- Tests run indefinitely without completing
- Import operations hang
- Database operations seem to freeze

**Root Causes:**
1. **Module-level database connections** - Database operations happening during import
2. **Real database access** - Tests connecting to user's actual database
3. **External editor calls** - Tests calling actual editor applications
4. **Network operations** - Database connections to remote servers

**Solutions:**
```python
# ❌ WRONG - Module level database connection
db_manager = DatabaseManager()  # At module level

# ✅ CORRECT - Lazy initialization
def get_db():
    return DatabaseManager()  # Only when called

# ✅ CORRECT - Dependency injection
def my_function(db_manager: DatabaseManager):
    # Use provided db_manager
```

**Verification:**
```bash
# Check for hanging imports
timeout 5s python -c "import fincli.cli" || echo "HANGING DETECTED"

# Check for real database access
lsof | grep tasks.db
```

### **Issue 2: Database Pollution in Tests**

**Symptoms:**
- Tests modify real user data
- Tests create files in user directories
- Tests fail when run multiple times

**Root Causes:**
1. **Missing test isolation** - Tests not using temporary databases
2. **Hardcoded paths** - Tests using real database paths
3. **Missing environment variables** - `FIN_DB_PATH` not set for tests

**Solutions:**
```python
# ❌ WRONG - Hardcoded database path
db_manager = DatabaseManager("~/fin/tasks.db")

# ✅ CORRECT - Use test fixture
def test_something(temp_db_path, monkeypatch):
    monkeypatch.setenv("FIN_DB_PATH", temp_db_path)
    db_manager = DatabaseManager(temp_db_path)
```

**Verification:**
```bash
# Check test isolation
timeout 30s python -m pytest tests/test_database.py -v

# Verify no real database access
strace -e trace=file python -c "import fincli.cli" 2>&1 | grep tasks.db
```

### **Issue 3: Import Errors or Circular Dependencies**

**Symptoms:**
- Import errors during testing
- Circular import warnings
- Module not found errors

**Root Causes:**
1. **Database operations at import time** - Functions called during module import
2. **Circular imports** - Modules importing each other
3. **Missing dependencies** - Required packages not installed

**Solutions:**
```python
# ❌ WRONG - Import-time execution
db_manager = DatabaseManager()  # Executes during import

# ✅ CORRECT - Lazy execution
def get_db():
    return DatabaseManager()  # Only executes when called
```

**Verification:**
```bash
# Test individual imports
timeout 5s python -c "import fincli.db" || echo "DB module issue"
timeout 5s python -c "import fincli.config" || echo "Config module issue"
timeout 5s python -c "import fincli.cli" || echo "CLI module issue"
```

### **Issue 4: Test Database Cleanup Failures**

**Symptoms:**
- Temporary database files left behind
- Tests fail on subsequent runs
- Disk space issues from test artifacts

**Root Causes:**
1. **Missing cleanup in fixtures** - Test databases not properly removed
2. **Exception handling** - Cleanup code not reached due to errors
3. **File permissions** - Cannot delete temporary files

**Solutions:**
```python
# ✅ CORRECT - Proper fixture cleanup
@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db_path = tmp.name
    
    yield temp_db_path
    
    # Cleanup
    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)
```

**Verification:**
```bash
# Check for leftover test files
find /tmp -name "*.db" -mtime +1

# Check test cleanup
python -m pytest tests/test_database.py -v --tb=short
```

### **Issue 5: Environment Variable Conflicts**

**Symptoms:**
- Tests use wrong database
- Inconsistent test behavior
- Real database accessed unexpectedly

**Root Causes:**
1. **Environment variable not set** - `FIN_DB_PATH` missing
2. **Wrong environment variable value** - Pointing to real database
3. **Environment variable override** - Other code changing the value

**Solutions:**
```python
# ✅ CORRECT - Explicit environment setting
def test_something(temp_db_path, monkeypatch):
    monkeypatch.setenv("FIN_DB_PATH", temp_db_path)
    
    # Verify environment is set
    assert os.environ.get("FIN_DB_PATH") == temp_db_path
    
    db_manager = DatabaseManager()
    # ... test logic
```

**Verification:**
```bash
# Check environment variables
echo "FIN_DB_PATH: $FIN_DB_PATH"

# Test with explicit environment
FIN_DB_PATH=/tmp/test.db python -c "import fincli.cli"
```

## 🔍 **Diagnostic Commands**

### **Check for Hanging Operations**
```bash
# Test basic Python
timeout 5s python -c "print('Python works')" || echo "Basic Python broken"

# Test module imports
timeout 5s python -c "import fincli.db; print('DB OK')" || echo "DB module hanging"
timeout 5s python -c "import fincli.config; print('Config OK')" || echo "Config module hanging"
timeout 5s python -c "import fincli.cli; print('CLI OK')" || echo "CLI module hanging"

# Test with environment variable
timeout 5s bash -c 'FIN_DB_PATH=/tmp/test.db python -c "import fincli.cli"' || echo "CLI with env hanging"
```

### **Check Database Connections**
```bash
# Check for active database connections
lsof | grep tasks.db

# Check for database locks
ls -la ~/fin/tasks.db*

# Test database accessibility
sqlite3 ~/fin/tasks.db "SELECT 1;" 2>/dev/null && echo "Database accessible" || echo "Database not accessible"
```

### **Check Test Isolation**
```bash
# Run tests with database monitoring
timeout 60s bash -c 'FIN_DB_PATH=/tmp/test.db python -m pytest tests/test_database.py -v' || echo "Tests hanging"

# Check for real database access
strace -e trace=file python -c "import fincli.cli" 2>&1 | grep tasks.db

# Quick isolation check
timeout 5s bash -c 'FIN_DB_PATH=/tmp/test.db python -c "import fincli.cli"' && echo "Isolation working" || echo "Isolation broken"
```

## 🛠️ **Debugging Tools**

### **Python Debugging**
```python
import logging
import os

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Check environment variables
print(f"FIN_DB_PATH: {os.environ.get('FIN_DB_PATH')}")
print(f"Current working directory: {os.getcwd()}")

# Check database path resolution
from fincli.db import DatabaseManager
db_manager = DatabaseManager()
print(f"Database path: {db_manager.db_path}")
```

### **Database Inspection**
```python
import sqlite3

# Connect to database
conn = sqlite3.connect("~/fin/tasks.db")
cursor = conn.cursor()

# Check schema
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables: {tables}")

# Check tasks
cursor.execute("SELECT COUNT(*) FROM tasks;")
count = cursor.fetchone()[0]
print(f"Task count: {count}")

conn.close()
```

### **Test Debugging**
```python
# Add debug output to tests
def test_something(temp_db_path, monkeypatch):
    print(f"Test using database: {temp_db_path}")
    
    monkeypatch.setenv("FIN_DB_PATH", temp_db_path)
    print(f"Environment FIN_DB_PATH: {os.environ.get('FIN_DB_PATH')}")
    
    db_manager = DatabaseManager(temp_db_path)
    print(f"Database manager path: {db_manager.db_path}")
    
    # ... rest of test
```

## 📋 **Prevention Checklist**

### **Before Committing Code**
- [ ] No `DatabaseManager()` calls at module level
- [ ] All database operations use dependency injection
- [ ] Tests use `temp_db_path` fixture
- [ ] Environment variables properly handled
- [ ] No hardcoded database paths

### **Before Running Tests**
- [ ] `FIN_DB_PATH` not set to real database
- [ ] No real database connections active
- [ ] Test environment properly isolated
- [ ] Dependencies installed and up to date

### **After Running Tests**
- [ ] All tests pass
- [ ] No temporary files left behind
- [ ] No real database modifications
- [ ] Test execution time reasonable (< 1 second per test)

## 🆘 **Getting Help**

### **When to Ask for Help**
- Tests hanging for more than 5 minutes
- Real database data corrupted
- Cannot resolve import errors
- Test isolation completely broken

### **Information to Provide**
- Error messages and stack traces
- Test output and execution time
- Environment variable values
- Database file locations and permissions
- Steps to reproduce the issue

### **Resources**
- `DEBUG_DATABASE_POLLUTION_PLAN.md` - Current implementation plan
- `DATABASE_OPERATIONS_GUIDE.md` - Best practices guide
- `TESTING.md` - Testing guidelines
- `tests/conftest.py` - Test isolation examples

---

**Remember**: Prevention is better than cure. Follow the best practices and use the diagnostic tools to catch issues early!
