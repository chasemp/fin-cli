#!/usr/bin/env python3
"""Debug script to trace TaskManager label processing."""

import os
import re
import sys

# Add the fincli module to the path
sys.path.insert(0, "/Users/cpettet/git/chasemp/fin-cli")


# Test the TaskManager label processing directly
def test_label_processing():
    labels = ["later"]
    print(f"Input labels: {labels}")

    # Simulate the TaskManager.add_task label processing logic
    labels_str = None
    if labels:
        # Normalize labels: split on comma or space, lowercase, trim whitespace
        all_labels = []
        for label_group in labels:
            if label_group:
                # Split on comma or space, then normalize each label
                split_labels = re.split(r"[, ]+", label_group.strip())
                print(f"  Processing label_group: {repr(label_group)}")
                print(f"  Split labels: {split_labels}")
                for label in split_labels:
                    if label.strip():
                        normalized = label.strip().lower()
                        print(f"    Adding normalized label: {repr(normalized)}")
                        all_labels.append(normalized)

        # Remove duplicates and sort
        unique_labels = sorted(list(set(all_labels)))
        labels_str = ",".join(unique_labels) if unique_labels else None
        print(f"  Unique labels: {unique_labels}")
        print(f"  Final labels_str: {repr(labels_str)}")

    return labels_str


if __name__ == "__main__":
    result = test_label_processing()
    print(f"\nFinal result that would be stored in database: {repr(result)}")
