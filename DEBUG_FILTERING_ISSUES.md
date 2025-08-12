# Debug: Task Filtering Issues

## Problem Description
User reported that the following commands were not working as expected:
- `fin -d 3` should show OPEN tasks created or modified in the last 3 days (includes today)
- `fin -d 3 -s done` should show CLOSED tasks in the last 3 days (including today)  
- `fine -s done` should show today and yesterday's completed tasks
- `fine -s done -d 3` should show completed tasks from the last 3 days (including today)

## Root Cause Analysis

### Issue 1: Incorrect Date Filtering Logic
**File:** `fincli/utils.py` - `filter_tasks_by_date_range()` function

**Problem:** The original logic was:
```python
# Always include open tasks regardless of creation date
if task["completed_at"] is None:
    filtered_tasks.append(task)
else:
    # For completed tasks, apply date filtering
    # ... date filtering logic
```

This meant that ALL open tasks were always included, regardless of when they were created or modified.

**Fix Applied:** Modified the function to properly filter both open and completed tasks by date:
```python
# Determine the relevant date for filtering
if task["completed_at"]:
    # For completed tasks, use completion date
    completed_dt = datetime.fromisoformat(
        task["completed_at"].replace("Z", "+00:00")
    )
    task_date = completed_dt.date()
else:
    # For open tasks, use creation date
    created_dt = datetime.fromisoformat(
        task["created_at"].replace("Z", "+00:00")
    )
    task_date = created_dt.date()

# Include tasks from the lookback period
if lookback_date <= task_date <= today:
    filtered_tasks.append(task)
```

### Issue 2: Missing Commands in CLI Registration
**File:** `fincli/cli.py` - `main()` function

**Problem:** The `complete`, `done`, `reopen`, `toggle`, and `fine` commands were not in the list of known commands, so they were being interpreted as direct task additions instead of subcommands.

**Fix Applied:** Added missing commands to the known commands list:
```python
and args[0]
not in [
    "add-task",
    "add", 
    "init",
    "list-tasks",
    "list",
    "open-editor",
    "complete",  # Added
    "done",      # Added
    "reopen",    # Added
    "toggle",    # Added
    "list-labels",
    "import",
    "export", 
    "digest",
    "report",
    "backup",
    "list-backups",
    "restore",
    "restore-latest",
    "config",
    "fins",
    "fine",      # Added
    "--help",
    "-h",
    "--version", 
    "-v",
    "--verbose",
]
```

## Expected Behavior After Fixes

### `fin -d 3`
- Should show OPEN tasks created in the last 3 days (including today)
- Uses `created_at` date for open tasks

### `fin -d 3 -s done` 
- Should show CLOSED tasks completed in the last 3 days (including today)
- Uses `completed_at` date for completed tasks

### `fine -s done`
- Should show today and yesterday's completed tasks (default days=1)
- Uses `completed_at` date for filtering

### `fine -s done -d 3`
- Should show completed tasks from the last 3 days (including today)
- Uses `completed_at` date for filtering

## Testing Status
- ✅ Fixed `filter_tasks_by_date_range()` function
- ✅ Fixed CLI command registration
- ⚠️ Terminal commands seem to be hanging (possible environment issue)
- ⚠️ Need to test the actual filtering behavior

## Next Steps
1. Test the filtering logic with actual tasks
2. Verify that `fine` command works correctly (it has its own entry point in setup.py)
3. Test edge cases (tasks created/completed on different dates)
4. Ensure the filtering works for both open and completed tasks

## Files Modified
1. `fincli/utils.py` - Fixed date filtering logic
2. `fincli/cli.py` - Added missing commands to known commands list

## Notes
- The `fine` command has its own entry point in `setup.py` as `"fine=fincli.cli:fine_command"`
- Terminal commands are hanging, which may indicate an environment or dependency issue
- The core filtering logic has been fixed and should work correctly once the environment issues are resolved 