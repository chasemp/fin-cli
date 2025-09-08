#!/usr/bin/env python3
"""Debug script to trace the full label processing flow."""

import os
import sys

# Add the fincli module to the path
sys.path.insert(0, "/Users/cpettet/git/chasemp/fin-cli")

from fincli.db import DatabaseManager
from fincli.tasks import TaskManager


def test_full_flow():
    print("Testing full TaskManager flow...")

    # Use a test database to avoid polluting the real one
    test_db_path = "/tmp/test_labels.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    try:
        # Create database manager (auto-initializes)
        db_manager = DatabaseManager(test_db_path)

        # Create task manager
        task_manager = TaskManager(db_manager)

        # Test adding a task with labels
        content = "Test task"
        labels = ["later", "urgent"]
        source = "cli"
        due_date = None
        context = "default"

        print(f"Adding task with:")
        print(f"  content: {repr(content)}")
        print(f"  labels: {repr(labels)}")
        print(f"  source: {repr(source)}")
        print(f"  due_date: {repr(due_date)}")
        print(f"  context: {repr(context)}")

        # Add the task
        task_id = task_manager.add_task(content, labels, source, due_date, context)
        print(f"Task added with ID: {task_id}")

        # Verify what was stored
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, content, labels FROM tasks WHERE id = ?", (task_id,))
            result = cursor.fetchone()
            if result:
                print(f"Stored in database:")
                print(f"  id: {result[0]}")
                print(f"  content: {repr(result[1])}")
                print(f"  labels: {repr(result[2])}")
            else:
                print("ERROR: Task not found in database!")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Clean up
        if os.path.exists(test_db_path):
            os.remove(test_db_path)


if __name__ == "__main__":
    test_full_flow()
