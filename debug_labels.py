#!/usr/bin/env python3
"""Debug script to trace label processing."""

import os
import re
import sys

# Add the fincli module to the path
sys.path.insert(0, "/Users/cpettet/git/chasemp/fin-cli")

from fincli.cli import handle_direct_task

# Mock the database operations to see what gets passed
original_add_task = None


def debug_add_task(content, labels, source="cli", due_date=None):
    print(f"DEBUG add_task called with:")
    print(f"  content: {repr(content)}")
    print(f"  labels: {repr(labels)}")
    print(f"  source: {repr(source)}")
    print(f"  due_date: {repr(due_date)}")

    # Don't actually add to database, just show what would be added
    return


# Patch the add_task function
import fincli.cli

fincli.cli.add_task = debug_add_task

# Test the problematic command
test_args = ["Initial Analysis- INFOSEC-2000", "#later"]
print(f"Testing with args: {test_args}")
print("=" * 50)

try:
    handle_direct_task(test_args)
except SystemExit:
    pass  # handle_direct_task calls sys.exit, which is normal
