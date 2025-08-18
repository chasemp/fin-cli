"""
CLI tests for Fin task tracking system
"""

import subprocess
import sys

from fincli.cli import cli


class TestCLI:
    """Test CLI functionality."""

    def test_cli_help(self, cli_runner):
        """Test CLI help output."""
        result = cli_runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "FinCLI - A lightweight task tracking system" in result.output
        assert "Manage your local task database" in result.output
        assert "add-task" in result.output
        assert "list-tasks" in result.output

    def test_cli_add_task_basic(self, cli_runner, temp_db_path, monkeypatch):
        """Test adding a basic task via CLI."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        result = cli_runner.invoke(cli, ["add-task", "Test task content"])

        assert result.exit_code == 0
        assert '✅ Task added: "Test task content"' in result.output

    def test_cli_add_task_with_labels(self, cli_runner, temp_db_path, monkeypatch):
        """Test adding a task with labels via CLI."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        result = cli_runner.invoke(
            cli,
            [
                "add-task",
                "Test task with labels",
                "--label",
                "work",
                "--label",
                "urgent",
            ],
        )

        assert result.exit_code == 0
        assert '✅ Task added: "Test task with labels" [urgent, work]' in result.output

    def test_cli_add_task_with_source(self, cli_runner, temp_db_path, monkeypatch):
        """Test adding a task with custom source via CLI."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        result = cli_runner.invoke(
            cli, ["add-task", "Test task with source", "--source", "test"]
        )

        assert result.exit_code == 0
        assert '✅ Task added: "Test task with source"' in result.output

    def test_cli_missing_content(self, cli_runner):
        """Test CLI with missing content argument."""
        result = cli_runner.invoke(cli, ["add-task"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_cli_empty_content(self, cli_runner):
        """Test CLI with empty content."""
        result = cli_runner.invoke(cli, ["add-task", ""])

        assert result.exit_code == 0
        assert '✅ Task added: ""' in result.output

    def test_cli_special_characters(self, cli_runner, temp_db_path, monkeypatch):
        """Test CLI with special characters in task content."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        special_content = (
            "Task with 'quotes', \"double quotes\", and special chars: @#$%^&*()"
        )
        result = cli_runner.invoke(cli, ["add-task", special_content])

        assert result.exit_code == 0
        assert f'✅ Task added: "{special_content}"' in result.output

    def test_cli_multiple_labels(self, cli_runner, temp_db_path, monkeypatch):
        """Test CLI with multiple labels."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        result = cli_runner.invoke(
            cli,
            [
                "add-task",
                "Complex task",
                "--label",
                "personal",
                "--label",
                "urgent",
                "--label",
                "work",
            ],
        )

        assert result.exit_code == 0
        assert '✅ Task added: "Complex task" [personal, urgent, work]' in result.output

    def test_cli_labels_normalization(self, cli_runner, temp_db_path, monkeypatch):
        """Test CLI label normalization."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        result = cli_runner.invoke(
            cli,
            [
                "add-task",
                "Task with mixed case labels",
                "--label",
                "TEST",
                "--label",
                "Urgent",
                "--label",
                "work",
            ],
        )

        assert result.exit_code == 0
        assert (
            '✅ Task added: "Task with mixed case labels" [test, urgent, work]'
            in result.output
        )

    def test_cli_empty_labels(self, cli_runner, temp_db_path, monkeypatch):
        """Test CLI with empty labels."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        result = cli_runner.invoke(
            cli,
            [
                "add-task",
                "Task with empty labels",
                "--label",
                "",
                "--label",
                "valid",
            ],
        )

        assert result.exit_code == 0
        assert '✅ Task added: "Task with empty labels" [valid]' in result.output

    def test_cli_reserved_word_validation_and(self, temp_db_path, monkeypatch):
        """Test that reserved word 'and' cannot be used as a label."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Mock sys.argv to simulate direct task addition
        import sys

        original_argv = sys.argv
        sys.argv = ["fin", "Test task #and"]

        try:
            import io
            from contextlib import redirect_stdout

            from fincli.cli import main

            # Capture stdout and catch SystemExit
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    main()
                except SystemExit:
                    pass  # Expected when validation fails

            output = f.getvalue()
            assert "Cannot use reserved words as labels: and" in output
            assert "Reserved words:" in output
            assert "and" in output
            assert "or" in output
            assert "ref" in output
            assert "due" in output
            assert "recur" in output
            assert "depends" in output
            assert "not" in output
        finally:
            sys.argv = original_argv

    def test_cli_reserved_word_validation_or(self, temp_db_path, monkeypatch):
        """Test that reserved word 'or' cannot be used as a label."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Mock sys.argv to simulate direct task addition
        import sys

        original_argv = sys.argv
        sys.argv = ["fin", "Test task #or"]

        try:
            import io
            from contextlib import redirect_stdout

            from fincli.cli import main

            # Capture stdout and catch SystemExit
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    main()
                except SystemExit:
                    pass  # Expected when validation fails

            output = f.getvalue()
            assert "Cannot use reserved words as labels: or" in output
            assert "Reserved words:" in output
            assert "and" in output
            assert "or" in output
            assert "ref" in output
            assert "due" in output
            assert "recur" in output
            assert "depends" in output
            assert "not" in output
        finally:
            sys.argv = original_argv

    def test_cli_reserved_word_validation_case_insensitive(
        self, temp_db_path, monkeypatch
    ):
        """Test that reserved word validation is case insensitive."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Mock sys.argv to simulate direct task addition
        import sys

        original_argv = sys.argv
        sys.argv = ["fin", "Test task #AND"]

        try:
            import io
            from contextlib import redirect_stdout

            from fincli.cli import main

            # Capture stdout and catch SystemExit
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    main()
                except SystemExit:
                    pass  # Expected when validation fails

            output = f.getvalue()
            assert "Cannot use reserved words as labels: AND" in output
        finally:
            sys.argv = original_argv

    def test_cli_normal_labels_still_work(self, temp_db_path, monkeypatch):
        """Test that normal labels still work after adding reserved word validation."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Mock sys.argv to simulate direct task addition
        import sys

        original_argv = sys.argv
        sys.argv = ["fin", "Test task #work"]

        try:
            import io
            from contextlib import redirect_stdout

            from fincli.cli import main

            # Capture stdout
            f = io.StringIO()
            with redirect_stdout(f):
                main()

            output = f.getvalue()
            assert '✅ Task added: "Test task" [work]' in output
        finally:
            sys.argv = original_argv

    def test_cli_reserved_word_validation_ref(self, temp_db_path, monkeypatch):
        """Test that reserved word 'ref' cannot be used as a label."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Mock sys.argv to simulate direct task addition
        import sys

        original_argv = sys.argv
        sys.argv = ["fin", "Test task #ref"]

        try:
            import io
            from contextlib import redirect_stdout

            from fincli.cli import main

            # Capture stdout and catch SystemExit
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    main()
                except SystemExit:
                    pass  # Expected when validation fails

            output = f.getvalue()
            assert "Cannot use reserved words as labels: ref" in output
            assert "Reserved words:" in output
        finally:
            sys.argv = original_argv

    def test_cli_reserved_word_validation_due(self, temp_db_path, monkeypatch):
        """Test that reserved word 'due' cannot be used as a label."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Mock sys.argv to simulate direct task addition
        import sys

        original_argv = sys.argv
        sys.argv = ["fin", "Test task #due"]

        try:
            import io
            from contextlib import redirect_stdout

            from fincli.cli import main

            # Capture stdout and catch SystemExit
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    main()
                except SystemExit:
                    pass  # Expected when validation fails

            output = f.getvalue()
            assert "Cannot use reserved words as labels: due" in output
            assert "Reserved words:" in output
        finally:
            sys.argv = original_argv

    def test_cli_reserved_word_validation_not(self, temp_db_path, monkeypatch):
        """Test that reserved word 'not' cannot be used as a label."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Mock sys.argv to simulate direct task addition
        import sys

        original_argv = sys.argv
        sys.argv = ["fin", "Test task #not"]

        try:
            import io
            from contextlib import redirect_stdout

            from fincli.cli import main

            # Capture stdout and catch SystemExit
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    main()
                except SystemExit:
                    pass  # Expected when validation fails

            output = f.getvalue()
            assert "Cannot use reserved words as labels: not" in output
            assert "Reserved words:" in output
        finally:
            sys.argv = original_argv

    def test_cli_due_date_parsing(self, temp_db_path, monkeypatch):
        """Test that due dates are parsed correctly."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Mock sys.argv to simulate direct task addition
        import sys

        original_argv = sys.argv
        sys.argv = ["fin", "Project deadline #due:2025-08-10"]

        try:
            import io
            from contextlib import redirect_stdout

            from fincli.cli import main

            # Capture stdout
            f = io.StringIO()
            with redirect_stdout(f):
                main()

            output = f.getvalue()
            assert '✅ Task added: "Project deadline" (due: 2025-08-10)' in output
        finally:
            sys.argv = original_argv

    def test_cli_recurring_task_parsing(self, temp_db_path, monkeypatch):
        """Test that recurring tasks are parsed correctly."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Mock sys.argv to simulate direct task addition
        import sys

        original_argv = sys.argv
        sys.argv = ["fin", "Daily standup #recur:daily"]

        try:
            import io
            from contextlib import redirect_stdout

            from fincli.cli import main

            # Capture stdout
            f = io.StringIO()
            with redirect_stdout(f):
                main()

            output = f.getvalue()
            assert '✅ Task added: "Daily standup" [recur:daily]' in output
        finally:
            sys.argv = original_argv

    def test_cli_dependency_parsing(self, temp_db_path, monkeypatch):
        """Test that task dependencies are parsed correctly."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Mock sys.argv to simulate direct task addition
        import sys

        original_argv = sys.argv
        sys.argv = ["fin", "Implement feature #depends:task123"]

        try:
            import io
            from contextlib import redirect_stdout

            from fincli.cli import main

            # Capture stdout
            f = io.StringIO()
            with redirect_stdout(f):
                main()

            output = f.getvalue()
            assert '✅ Task added: "Implement feature" [depends:task123]' in output
        finally:
            sys.argv = original_argv

    def test_cli_complex_label_combinations_and(self, temp_db_path, monkeypatch):
        """Test AND logic in complex label combinations."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Add some test tasks first
        import sys

        original_argv = sys.argv

        # Add tasks with different label combinations
        test_tasks = [
            ["fin", "Work task #work"],
            ["fin", "Urgent work task #work #urgent"],
            ["fin", "Personal task #personal"],
        ]

        try:
            import io
            from contextlib import redirect_stdout

            from click.exceptions import Exit

            from fincli.cli import main

            # Add test tasks
            for task_args in test_tasks:
                sys.argv = task_args
                f = io.StringIO()
                with redirect_stdout(f):
                    try:
                        main()
                    except (SystemExit, Exit):
                        pass  # Expected when command completes

            # Test AND filtering
            sys.argv = ["fin", "list", "-l", "work and urgent"]
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    main()
                except (SystemExit, Exit):
                    pass  # Expected when command completes

            output = f.getvalue()
            assert "Urgent work task" in output
            assert (
                "Work task" not in output
            )  # Should not appear (only has work, not urgent)
            assert "Personal task" not in output  # Should not appear (has neither)
        finally:
            sys.argv = original_argv

    def test_cli_complex_label_combinations_or(self, temp_db_path, monkeypatch):
        """Test OR logic in complex label combinations."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Add some test tasks first
        import sys

        original_argv = sys.argv

        # Add tasks with different label combinations
        test_tasks = [
            ["fin", "Work task #work"],
            ["fin", "Urgent work task #work #urgent"],
            ["fin", "Personal task #personal"],
        ]

        try:
            import io
            from contextlib import redirect_stdout

            from click.exceptions import Exit

            from fincli.cli import main

            # Add test tasks
            for task_args in test_tasks:
                sys.argv = task_args
                f = io.StringIO()
                with redirect_stdout(f):
                    try:
                        main()
                    except (SystemExit, Exit):
                        pass  # Expected when command completes

            # Test OR filtering
            sys.argv = ["fin", "list", "-l", "work or personal"]
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    main()
                except (SystemExit, Exit):
                    pass  # Expected when command completes

            output = f.getvalue()
            assert "Work task" in output
            assert "Urgent work task" in output  # Has work label
            assert "Personal task" in output
        finally:
            sys.argv = original_argv

    def test_cli_multiple_criteria_filtering(self, temp_db_path, monkeypatch):
        """Test multiple criteria filtering."""
        # Mock the database path and set environment variable
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )
        monkeypatch.setenv("FIN_DB_PATH", temp_db_path)

        # Add some test tasks first
        import sys

        original_argv = sys.argv

        # Add tasks with different label combinations
        test_tasks = [
            ["fin", "Work task #work"],
            ["fin", "Urgent work task #work #urgent"],
            ["fin", "Personal task #personal"],
        ]

        try:
            import io
            from contextlib import redirect_stdout

            from click.exceptions import Exit

            from fincli.cli import main

            # Add test tasks
            for task_args in test_tasks:
                sys.argv = task_args
                f = io.StringIO()
                with redirect_stdout(f):
                    try:
                        main()
                    except (SystemExit, Exit):
                        pass  # Expected when command completes

            # Test multiple criteria (should match any of the criteria)
            sys.argv = ["fin", "list", "-l", "work and urgent", "-l", "personal"]
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    main()
                except (SystemExit, Exit):
                    pass  # Expected when command completes

            output = f.getvalue()
            assert "Urgent work task" in output  # Matches "work and urgent"
            assert "Personal task" in output  # Matches "personal"
            assert "Work task" not in output  # Only has work, not urgent
        finally:
            sys.argv = original_argv


class TestCLIExecution:
    """Test CLI execution via subprocess."""

    def test_cli_execution_basic(self, temp_db_path, monkeypatch):
        """Test basic CLI execution via subprocess."""
        # Test CLI help
        result = subprocess.run(
            [sys.executable, "-m", "fincli.cli", "--help"],
            capture_output=True,
            text=True,
            env={"FIN_DB_PATH": temp_db_path},
        )

        assert result.returncode == 0
        assert "FinCLI - A lightweight task tracking system" in result.stdout

        # Test adding a task
        result = subprocess.run(
            [sys.executable, "-m", "fincli.cli", "add-task", "Integration test task"],
            capture_output=True,
            text=True,
            env={"FIN_DB_PATH": temp_db_path},
        )

        assert result.returncode == 0
        assert "Task added" in result.stdout

    def test_cli_execution_with_labels(self, temp_db_path, monkeypatch):
        """Test CLI execution with labels."""
        # Test adding a task with labels
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "fincli.cli",
                "add-task",
                "Task with labels",
                "--label",
                "work",
                "--label",
                "urgent",
            ],
            capture_output=True,
            text=True,
            env={"FIN_DB_PATH": temp_db_path},
        )

        assert result.returncode == 0
        assert "Task added" in result.stdout
        assert "work" in result.stdout
        assert "urgent" in result.stdout

    def test_cli_execution_error_handling(self, temp_db_path, monkeypatch):
        """Test CLI error handling."""
        # Test missing argument
        result = subprocess.run(
            [sys.executable, "-m", "fincli.cli", "add-task"],
            capture_output=True,
            text=True,
            env={"FIN_DB_PATH": temp_db_path},
        )

        assert result.returncode != 0
        assert "Missing argument" in result.stderr

    def test_cli_execution_help(self, temp_db_path, monkeypatch):
        """Test CLI help execution."""
        # Test help command
        result = subprocess.run(
            [sys.executable, "-m", "fincli.cli", "--help"],
            capture_output=True,
            text=True,
            env={"FIN_DB_PATH": temp_db_path},
        )

        assert result.returncode == 0
        assert "Usage:" in result.stdout


class TestCLIOutput:
    """Test CLI output formatting."""

    def test_output_format_basic(self, cli_runner, temp_db_path, monkeypatch):
        """Test basic CLI output format."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        result = cli_runner.invoke(cli, ["add-task", "Simple task"])

        assert result.exit_code == 0
        assert '✅ Task added: "Simple task"' in result.output

    def test_output_format_with_labels(self, cli_runner, temp_db_path, monkeypatch):
        """Test CLI output format with labels."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        result = cli_runner.invoke(
            cli, ["add-task", "Task with labels", "--label", "work"]
        )

        assert result.exit_code == 0
        assert '✅ Task added: "Task with labels" [work]' in result.output

    def test_output_format_multiple_labels(self, cli_runner, temp_db_path, monkeypatch):
        """Test CLI output format with multiple labels."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        result = cli_runner.invoke(
            cli,
            [
                "add-task",
                "Task with multiple labels",
                "--label",
                "personal",
                "--label",
                "urgent",
                "--label",
                "work",
            ],
        )

        assert result.exit_code == 0
        assert (
            '✅ Task added: "Task with multiple labels" [personal, urgent, work]'
            in result.output
        )


class TestCLIBackup:
    """Test CLI backup functionality."""

    def test_backup_create(self, cli_runner, temp_db_path, monkeypatch):
        """Test creating a backup via CLI."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        # Add a task first
        result = cli_runner.invoke(cli, ["add-task", "Test task for backup"])
        assert result.exit_code == 0

        # Create backup
        result = cli_runner.invoke(cli, ["backup", "-d", "Test backup"])
        assert result.exit_code == 0
        assert "✅ Backup created: backup_" in result.output

    def test_backup_list(self, cli_runner, temp_db_path, monkeypatch):
        """Test listing backups via CLI."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        # Create a backup first
        result = cli_runner.invoke(cli, ["backup", "-d", "Test backup"])
        assert result.exit_code == 0

        # List backups
        result = cli_runner.invoke(cli, ["list-backups"])
        assert result.exit_code == 0
        assert "Available backups:" in result.output
        assert "backup_" in result.output

    def test_backup_restore(self, cli_runner, temp_db_path, monkeypatch):
        """Test restoring from backup via CLI."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        # Add initial task
        result = cli_runner.invoke(cli, ["add-task", "Original task"])
        assert result.exit_code == 0

        # Create backup
        result = cli_runner.invoke(cli, ["backup", "-d", "Initial backup"])
        assert result.exit_code == 0
        backup_output = result.output
        backup_id = backup_output.split("backup_")[1].split()[0]

        # Add another task
        result = cli_runner.invoke(cli, ["add-task", "New task"])
        assert result.exit_code == 0

        # Verify we have 2 tasks
        result = cli_runner.invoke(cli, ["list-tasks", "-s", "all"])
        assert result.exit_code == 0
        assert "Original task" in result.output
        assert "New task" in result.output

        # Restore from backup
        result = cli_runner.invoke(cli, ["restore", backup_id, "--force"])
        assert result.exit_code == 0
        assert f"✅ Successfully restored from backup_{backup_id}" in result.output

        # Verify we're back to 1 task
        result = cli_runner.invoke(cli, ["list-tasks", "-s", "all"])
        assert result.exit_code == 0
        assert "Original task" in result.output
        assert "New task" not in result.output

    def test_backup_restore_latest(self, cli_runner, temp_db_path, monkeypatch):
        """Test restoring from latest backup via CLI."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        # Add initial task
        result = cli_runner.invoke(cli, ["add-task", "Original task"])
        assert result.exit_code == 0

        # Create backup
        result = cli_runner.invoke(cli, ["backup", "-d", "Initial backup"])
        assert result.exit_code == 0

        # Add another task
        result = cli_runner.invoke(cli, ["add-task", "New task"])
        assert result.exit_code == 0

        # Restore from latest backup
        result = cli_runner.invoke(cli, ["restore-latest", "--force"])
        assert result.exit_code == 0
        assert "✅ Successfully restored from backup_" in result.output

        # Verify we're back to 1 task
        result = cli_runner.invoke(cli, ["list-tasks", "-s", "all"])
        assert result.exit_code == 0
        assert "Original task" in result.output
        assert "New task" not in result.output
