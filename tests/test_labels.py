"""
Tests for label functionality
"""



from fincli.cli import list_labels
from fincli.db import DatabaseManager


class TestLabelNormalization:
    """Test label normalization functionality."""

    def test_label_normalization_comma_separated(self, db_manager):
        """Test normalizing comma-separated labels."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task_id = task_manager.add_task("Test task", labels=["Planning, infra "])
        task = task_manager.get_task(task_id)

        assert task["labels"] == ["infra", "planning"]

    def test_label_normalization_space_separated(self, db_manager):
        """Test normalizing space-separated labels."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task_id = task_manager.add_task("Test task", labels=["work  urgent"])
        task = task_manager.get_task(task_id)

        assert task["labels"] == ["urgent", "work"]

    def test_label_normalization_mixed(self, db_manager):
        """Test normalizing mixed comma and space separated labels."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task_id = task_manager.add_task("Test task", labels=["work, urgent personal"])
        task = task_manager.get_task(task_id)

        assert task["labels"] == ["personal", "urgent", "work"]

    def test_label_normalization_duplicates(self, db_manager):
        """Test that duplicate labels are removed."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task_id = task_manager.add_task("Test task", labels=["work", "WORK", "Work"])
        task = task_manager.get_task(task_id)

        assert task["labels"] == ["work"]

    def test_label_normalization_empty(self, db_manager):
        """Test handling of empty labels."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task_id = task_manager.add_task("Test task", labels=["", "  ", "work"])
        task = task_manager.get_task(task_id)

        assert task["labels"] == ["work"]

    def test_label_normalization_none(self, db_manager):
        """Test handling of None labels."""
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        task_id = task_manager.add_task("Test task", labels=None)
        task = task_manager.get_task(task_id)

        assert task["labels"] == []


class TestGetAllLabels:
    """Test getting all labels from database."""

    def test_get_all_labels_empty(self, db_manager):
        """Test getting labels when no tasks exist."""
        from fincli.labels import LabelManager

        label_manager = LabelManager(db_manager)
        labels = label_manager.get_all_labels()
        assert labels == []

    def test_get_all_labels_single_task(self, db_manager):
        """Test getting labels from a single task."""
        from fincli.labels import LabelManager
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        label_manager = LabelManager(db_manager)

        task_manager.add_task("Test task", labels=["work", "urgent"])
        labels = label_manager.get_all_labels()

        assert labels == ["urgent", "work"]

    def test_get_all_labels_multiple_tasks(self, db_manager):
        """Test getting labels from multiple tasks."""
        from fincli.labels import LabelManager
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        label_manager = LabelManager(db_manager)

        task_manager.add_task("Task 1", labels=["work", "urgent"])
        task_manager.add_task("Task 2", labels=["personal", "work"])
        task_manager.add_task("Task 3", labels=["planning"])

        labels = label_manager.get_all_labels()

        assert labels == ["personal", "planning", "urgent", "work"]

    def test_get_all_labels_no_labels(self, db_manager):
        """Test getting labels when tasks have no labels."""
        from fincli.labels import LabelManager
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        label_manager = LabelManager(db_manager)

        task_manager.add_task("Task 1")
        task_manager.add_task("Task 2")

        labels = label_manager.get_all_labels()
        assert labels == []


class TestFilterTasksByLabel:
    """Test filtering tasks by label."""

    def test_filter_by_label_exact_match(self, db_manager):
        """Test filtering by exact label match."""
        from fincli.labels import LabelManager
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        label_manager = LabelManager(db_manager)

        task_manager.add_task("Work task", labels=["work"])
        task_manager.add_task("Personal task", labels=["personal"])
        task_manager.add_task("Another work task", labels=["work", "urgent"])

        tasks = label_manager.filter_tasks_by_label("work")

        assert len(tasks) == 2
        for task in tasks:
            assert "work" in task["labels"]

    def test_filter_by_label_case_insensitive(self, db_manager):
        """Test that label filtering is case-insensitive."""
        from fincli.labels import LabelManager
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        label_manager = LabelManager(db_manager)

        task_manager.add_task("Work task", labels=["WORK"])
        task_manager.add_task("Personal task", labels=["personal"])

        tasks = label_manager.filter_tasks_by_label("work")

        assert len(tasks) == 1
        assert tasks[0]["content"] == "Work task"

    def test_filter_by_label_partial_match(self, db_manager):
        """Test filtering by partial label match."""
        from fincli.labels import LabelManager
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        label_manager = LabelManager(db_manager)

        task_manager.add_task("Infra task", labels=["infrastructure"])
        task_manager.add_task("Infra ops task", labels=["infra-ops"])
        task_manager.add_task("Personal task", labels=["personal"])

        tasks = label_manager.filter_tasks_by_label("infra")

        assert len(tasks) == 2
        for task in tasks:
            assert any("infra" in label.lower() for label in task["labels"])

    def test_filter_by_label_no_match(self, db_manager):
        """Test filtering when no tasks match the label."""
        from fincli.labels import LabelManager
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        label_manager = LabelManager(db_manager)

        task_manager.add_task("Work task", labels=["work"])
        task_manager.add_task("Personal task", labels=["personal"])

        tasks = label_manager.filter_tasks_by_label("nonexistent")

        assert len(tasks) == 0

    def test_filter_by_label_include_completed(self, db_manager):
        """Test filtering includes completed tasks by default."""
        from fincli.labels import LabelManager
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        label_manager = LabelManager(db_manager)

        # Add a task and mark it as completed
        task_id = task_manager.add_task("Completed work task", labels=["work"])
        import sqlite3

        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (task_id,),
            )
            conn.commit()

        tasks = label_manager.filter_tasks_by_label("work")

        assert len(tasks) == 1
        assert tasks[0]["completed_at"] is not None

    def test_filter_by_label_exclude_completed(self, db_manager):
        """Test filtering excludes completed tasks when specified."""
        from fincli.labels import LabelManager
        from fincli.tasks import TaskManager

        task_manager = TaskManager(db_manager)
        label_manager = LabelManager(db_manager)

        # Add a task and mark it as completed
        task_id = task_manager.add_task("Completed work task", labels=["work"])
        import sqlite3

        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (task_id,),
            )
            conn.commit()

        tasks = label_manager.filter_tasks_by_label("work", include_completed=False)

        assert len(tasks) == 0


class TestListLabelsCommand:
    """Test the list-labels command."""

    def test_list_labels_command_empty(self, cli_runner, temp_db_path, monkeypatch):
        """Test list-labels command when no labels exist."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        result = cli_runner.invoke(list_labels)

        assert result.exit_code == 0
        assert "No labels found in any tasks" in result.output

    def test_list_labels_command_with_labels(
        self, cli_runner, temp_db_path, monkeypatch
    ):
        """Test list-labels command when labels exist."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )

        # Add tasks with labels
        from fincli.tasks import TaskManager

        db_manager = DatabaseManager(temp_db_path)
        task_manager = TaskManager(db_manager)
        task_manager.add_task("Task 1", labels=["work", "urgent"])
        task_manager.add_task("Task 2", labels=["personal", "work"])

        result = cli_runner.invoke(list_labels)

        assert result.exit_code == 0
        assert "Known labels:" in result.output
        assert "- personal" in result.output
        assert "- urgent" in result.output
        assert "- work" in result.output


class TestLabelFilteringInCommands:
    """Test label filtering in CLI commands."""

    def test_fins_with_label_filter(self, cli_runner, temp_db_path, monkeypatch):
        """Test fins command with label filtering."""
        # Mock the database path
        monkeypatch.setattr(
            "fincli.db.DatabaseManager.__init__",
            lambda self, db_path=None: self._init_mock_db(temp_db_path),
        )


    def test_fine_with_label_filter(self, cli_runner):
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False, dir="/tmp")
        tmp.close()
        db_path = tmp.name
        try:
            os.environ["FIN_DB_PATH"] = db_path
            from fincli.db import DatabaseManager
            from fincli.tasks import TaskManager
            db_manager = DatabaseManager()
            task_manager = TaskManager(db_manager)
            task_manager.add_task("Work task", labels=["work"])
            task_manager.add_task("Personal task", labels=["personal"])
            pass
            del db_manager
            del task_manager
            from fincli.cli import open_editor
            def mock_subprocess_run(cmd, **kwargs):
                import os
                temp_file_path = cmd[-1] if cmd else None
                if temp_file_path and os.path.exists(temp_file_path):
                    with open(temp_file_path, "r") as f:
                        content = f.read()
                    content = content.replace("[ ]", "[x]", 1)
                    with open(temp_file_path, "w") as f:
                        f.write(content)
                class MockResult:
                    returncode = 0
                return MockResult()
            import pytest
            monkeypatch = pytest.MonkeyPatch()
            monkeypatch.setattr("subprocess.run", mock_subprocess_run)
            result = cli_runner.invoke(open_editor, ["--label", "work"])
            monkeypatch.undo()
            assert result.exit_code == 0
            assert "📝 Opening 1 tasks in editor..." in result.output
        finally:
            os.unlink(db_path)
