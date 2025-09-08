#!/usr/bin/env python3
"""Debug script to test the CLI add_task function directly."""

import os
import sys

# Add the fincli module to the path
sys.path.insert(0, "/Users/cpettet/git/chasemp/fin-cli")

# Set environment variable to use a test database
test_db_path = "/tmp/test_cli_labels.db"
if os.path.exists(test_db_path):
    os.remove(test_db_path)

os.environ["FIN_DB_PATH"] = test_db_path

try:
    from fincli.cli import add_task
    from fincli.db import DatabaseManager

    print("Testing CLI add_task function...")

    # Test the actual add_task function
    content = "Test task from CLI"
    labels = ("later", "urgent")
    source = "cli"
    due_date = None

    print(f"Calling add_task with:")
    print(f"  content: {repr(content)}")
    print(f"  labels: {repr(labels)}")
    print(f"  source: {repr(source)}")
    print(f"  due_date: {repr(due_date)}")

    # Call the function
    add_task(content, labels, source, due_date)

    # Verify what was stored
    db_manager = DatabaseManager(test_db_path)
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, content, labels FROM tasks ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        if result:
            print(f"Stored in database:")
            print(f"  id: {result[0]}")
            print(f"  content: {repr(result[1])}")
            print(f"  labels: {repr(result[2])}")
        else:
            print("ERROR: No task found in database!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
finally:
    # Clean up
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
