#!/usr/bin/env python3
"""
Comprehensive test runner for Fin task tracking system
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_python_tests(test_type=None, verbose=False):
    """Run Python tests using pytest."""
    print("🐍 Running Python tests...")

    cmd = [sys.executable, "-m", "pytest"]

    if test_type:
        cmd.extend(["-m", test_type])

    if verbose:
        cmd.append("-v")

    cmd.append("tests/")

    result = subprocess.run(cmd)
    return result.returncode == 0


def run_shell_tests():
    """Run shell script tests."""
    print("🐚 Running shell tests...")

    shell_test_path = Path("tests/test_shell.sh")
    if not shell_test_path.exists():
        print("❌ Shell test file not found")
        return False

    result = subprocess.run(
        ["bash", str(shell_test_path)], capture_output=True, text=True
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def run_integration_tests():
    """Run integration tests."""
    print("🔗 Running integration tests...")

    # Test the actual CLI with real database
    test_commands = [
        ["python", "-m", "fincli.cli", "--help"],
        ["python", "-m", "fincli.cli", "Integration test task"],
        [
            "python",
            "-m",
            "fincli.cli",
            "Task with labels",
            "--label",
            "test",
        ],
    ]

    all_passed = True

    for cmd in test_commands:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Command succeeded")
        else:
            print(f"❌ Command failed: {result.stderr}")
            all_passed = False

    return all_passed


def run_performance_tests():
    """Run performance tests."""
    print("⚡ Running performance tests...")

    import tempfile
    import time

    from fincli.db import DatabaseManager

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        db_manager = DatabaseManager(db_path)

        # Test bulk insert performance
        start_time = time.time()

        for i in range(100):
            db_manager.add_task(f"Performance test task {i}")

        end_time = time.time()
        duration = end_time - start_time

        print(f"✅ Added 100 tasks in {duration:.2f} seconds")
        print(f"   Average: {duration/100:.4f} seconds per task")

        # Test query performance
        start_time = time.time()
        tasks = db_manager.list_tasks()
        end_time = time.time()

        print(f"✅ Queried {len(tasks)} tasks in {end_time - start_time:.4f} seconds")

        return True

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def run_coverage_tests():
    """Run tests with coverage reporting."""
    print("📊 Running coverage tests...")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=fin",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "tests/",
    ]

    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Run Fin test suite")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "cli", "database", "all"],
        default="all",
        help="Type of tests to run",
    )
    parser.add_argument("--shell", action="store_true", help="Run shell tests")
    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests"
    )
    parser.add_argument("--coverage", action="store_true", help="Run coverage tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print("🧪 Fin Test Suite")
    print("=" * 50)

    all_passed = True

    # Run Python tests
    if args.type in ["all", "unit", "integration", "cli", "database"]:
        test_type = None if args.type == "all" else args.type
        if not run_python_tests(test_type, args.verbose):
            all_passed = False

    # Run shell tests
    if args.shell or args.type == "all":
        if not run_shell_tests():
            all_passed = False

    # Run integration tests
    if args.type in ["all", "integration"]:
        if not run_integration_tests():
            all_passed = False

    # Run performance tests
    if args.performance:
        if not run_performance_tests():
            all_passed = False

    # Run coverage tests
    if args.coverage:
        if not run_coverage_tests():
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
