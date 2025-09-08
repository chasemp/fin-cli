#!/usr/bin/env python3
"""Debug script to simulate the exact command line parsing."""

import os
import sys

# Add the fincli module to the path
sys.path.insert(0, "/Users/cpettet/git/chasemp/fin-cli")

# Simulate the exact command line arguments
# When you run: fin 'Debug test task' #debug
# sys.argv becomes: ['fin', 'Debug test task', '#debug']
# So sys.argv[1:] becomes: ['Debug test task', '#debug']

test_args = ["Debug test task", "#debug"]
print(f"Simulating command: fin {' '.join(repr(arg) for arg in test_args)}")
print(f"args = {test_args}")

# Simulate handle_direct_task logic
task_content = []
labels = []
source = "cli"
i = 0

while i < len(test_args):
    if test_args[i] == "--label" or test_args[i] == "-l":
        if i + 1 < len(test_args):
            labels.append(test_args[i + 1])
            i += 2
        else:
            print("Error: --label requires a value")
            sys.exit(1)
    elif test_args[i] == "--source":
        if i + 1 < len(test_args):
            source = test_args[i + 1]
            i += 2
        else:
            print("Error: --source requires a value")
            sys.exit(1)
    elif test_args[i].startswith("-"):
        # Skip other options for now
        i += 1
    else:
        task_content.append(test_args[i])
        i += 1

print(f"task_content after parsing: {task_content}")

if not task_content:
    print("Missing task content")
    sys.exit(1)

content = " ".join(task_content)
print(f"content after joining: {repr(content)}")

# Extract hashtags
import re

hashtags = re.findall(r"#(?!task\d+|ref:task\d+|due:|recur:|depends:)(\w+)", content)
print(f"hashtags found: {hashtags}")

for hashtag in hashtags:
    labels.append(hashtag)

print(f"labels after adding hashtags: {labels}")

# Remove hashtags from content
content = re.sub(r"#(task\d+|ref:task\d+)", r"__TASK_REF_\1__", content)
content = re.sub(r"#\w+", "", content)
content = re.sub(r"__TASK_REF_(task\d+|ref:task\d+)__", r"#\1", content)
content = re.sub(r"\s+", " ", content).strip()

print(f"final content: {repr(content)}")
print(f"final labels: {labels}")
