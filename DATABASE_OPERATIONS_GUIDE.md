# Database Operations Guide for FinCLI

## 🎯 **Overview**

This guide provides best practices for implementing database operations in FinCLI, ensuring proper test isolation, dependency injection, and maintainable code.

## 🚨 **Critical Rules (Never Violate)**

### **Rule 1: No Database Connections at Import Time**
```python
# ❌ WRONG - Module level
db_manager = DatabaseManager()  # NEVER at module level

# ✅ CORRECT - Function level or dependency injection
def get_db():
    return DatabaseManager()  # Only when called

# ✅ CORRECT - Dependency injection
def import_tasks(db_manager: DatabaseManager):
    # Use provided db_manager
```

### **Rule 2: Always Use Test Environment Variables**
```python
# ❌ WRONG - Hardcoded paths
db_path = "~/fin/tasks.db"

# ✅ CORRECT - Environment variable
db_path = os.environ.get("FIN_DB_PATH", "~/fin/tasks.db")
```

### **Rule 3: Test Isolation is Non-Negotiable**
- Tests must NEVER connect to real databases
- Tests must NEVER modify real user data
- Tests must use isolated, temporary databases
- Test cleanup must be 100% reliable

### **Rule 4: Dependency Injection for Database Operations**
```python
# ❌ WRONG - Internal creation
def import_tasks():
    db_manager = DatabaseManager()  # Creates its own

# ✅ CORRECT - Dependency injection
def import_tasks(db_manager: DatabaseManager):
    # Use provided db_manager
```

## 🔧 **Implementation Patterns**

### **Pattern 1: Lazy Database Initialization**
```python
class TaskManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def add_task(self, content: str, labels: List[str] = None):
        # Database operations only when method is called
        with self.db_manager.get_connection() as conn:
            # ... database operations
```

### **Pattern 2: Dependency Injection in Functions**
```python
def import_from_source(source: str, db_manager: Optional[DatabaseManager] = None, **kwargs):
    """
    Import tasks from a specific source.
    
    Args:
        source: Source name
        db_manager: Database manager instance (optional, will create one if not provided)
        **kwargs: Additional arguments
    """
    # Initialize managers - use provided db_manager or create one
    if db_manager is None:
        db_manager = DatabaseManager()
    
    # Use the database manager
    task_manager = TaskManager(db_manager)
    # ... rest of implementation
```

### **Pattern 3: Explicit Dependency Injection**
```python
def import_from_source_with_db(source: str, db_manager: DatabaseManager, **kwargs):
    """
    Import tasks from a specific source with explicit database manager.
    
    This function ensures dependency injection is used and prevents
    the importer from creating its own database connection.
    """
    importer_func = SOURCES[source]
    return importer_func(db_manager=db_manager, **kwargs)
```

## 🧪 **Testing Patterns**

### **Test Database Setup**
```python
def test_something(temp_db_path, monkeypatch):
    """Test with isolated database."""
    # Set environment variable to use temp database
    monkeypatch.setenv("FIN_DB_PATH", temp_db_path)
    
    # Use the fixture-provided database manager
    db_manager = DatabaseManager(temp_db_path)
    task_manager = TaskManager(db_manager)
    
    # Your test logic here
```

### **Using Fixture-Provided Database Managers**
```python
def test_with_fixture(db_manager):
    """Test using fixture-provided database manager."""
    task_manager = TaskManager(db_manager)
    
    # Add test data
    task_id = task_manager.add_task("Test task", labels=["test"])
    
    # Verify results
    task = task_manager.get_task(task_id)
    assert task["content"] == "Test task"
```

### **Testing Dependency Injection**
```python
def test_dependency_injection(temp_db_path):
    """Test that dependency injection works correctly."""
    db_manager = DatabaseManager(temp_db_path)
    
    # Test with explicit db_manager
    result = import_from_source_with_db("csv", db_manager, file_path="test.csv")
    assert result["success"] is True
    
    # Test with None db_manager (should create its own)
    result = import_from_source("csv", file_path="test.csv")
    assert result["success"] is True
```

## 📁 **File Organization**

### **Core Database Files**
- `fincli/db.py` - Database connection and schema management
- `fincli/tasks.py` - Task CRUD operations
- `fincli/labels.py` - Label management operations

### **Intake Modules (Updated)**
- `fincli/intake/text_importer.py` - Text file import with DI
- `fincli/intake/csv_importer.py` - CSV file import with DI
- `fincli/intake/json_importer.py` - JSON file import with DI
- `fincli/intake/__init__.py` - Intake module coordination with DI

### **Test Files**
- `tests/conftest.py` - Test isolation fixtures
- `tests/test_database.py` - Database operation tests
- `tests/test_integration.py` - Integration tests

## 🔍 **Database Connection Flow**

### **Normal Operation**
1. User calls CLI command
2. CLI creates `DatabaseManager()` instance
3. CLI passes `db_manager` to business logic functions
4. Business logic uses provided `db_manager`

### **Testing Operation**
1. Test fixture creates temporary database
2. Test fixture sets `FIN_DB_PATH` environment variable
3. Test creates `DatabaseManager(temp_db_path)` instance
4. Test passes `db_manager` to functions under test
5. Functions use provided `db_manager` (no internal creation)

### **Intake Module Operation**
1. User calls import function
2. If `db_manager` provided: use it directly
3. If `db_manager` not provided: create new instance
4. Import function uses `db_manager` for database operations

## 🚀 **Best Practices**

### **Code Organization**
1. **Separate concerns**: Database operations in dedicated classes
2. **Single responsibility**: Each class handles one type of operation
3. **Dependency injection**: Pass database managers as parameters
4. **Lazy initialization**: Only connect to database when needed

### **Error Handling**
```python
def safe_database_operation(db_manager: DatabaseManager):
    try:
        with db_manager.get_connection() as conn:
            # ... database operations
    except sqlite3.Error as e:
        # Handle database-specific errors
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        # Handle other errors
        logger.error(f"Unexpected error: {e}")
        raise
```

### **Resource Management**
```python
def managed_database_operation(db_manager: DatabaseManager):
    # Use context manager for automatic cleanup
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        # ... operations
        conn.commit()  # Explicit commit for data modifications
    # Connection automatically closed
```

## 📊 **Current Implementation Status**

### **✅ Completed**
- Test isolation fixtures in `conftest.py`
- Lazy database initialization in core modules
- Environment variable handling
- Temporary database usage in tests
- Intake modules refactored for dependency injection
- Test files updated to use fixture-provided database managers

### **🔧 In Progress**
- Documentation updates
- Code quality improvements

### **📋 Planned**
- Pre-commit hooks for database operation validation
- Linting rules for module-level database operations
- Import-time validation
- Automated checks for database pollution prevention

## 🎯 **Success Metrics**

### **Code Quality**
- No module-level `DatabaseManager()` calls
- All database operations use dependency injection
- Consistent error handling patterns
- Proper resource management

### **Test Reliability**
- 100% test isolation from real databases
- Fast test execution (< 1 second per test)
- No hanging or blocking operations
- Consistent test results

### **Maintainability**
- Clear separation of concerns
- Easy to understand database operation patterns
- Simple to add new database operations
- Clear documentation and examples

## 📚 **Additional Resources**

- `TESTING.md` - Comprehensive testing guidelines
- `DEBUG_DATABASE_POLLUTION_PLAN.md` - Current implementation plan
- `tests/conftest.py` - Test isolation implementation examples
- `fincli/intake/` - Dependency injection examples

---

**Remember**: Database operations should be predictable, testable, and maintainable. Always use dependency injection and test isolation!
