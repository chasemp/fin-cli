"""
Unit tests for Google Sheets connector functionality.
"""

from unittest.mock import MagicMock, Mock, patch

from google.oauth2.credentials import Credentials
import pytest

from fincli.sheets_connector import SheetsReader


class TestSheetsReader:
    """Test the SheetsReader class."""

    def test_init(self):
        """Test SheetsReader initialization."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        with patch("fincli.sheets_connector.build") as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service

            reader = SheetsReader(mock_creds, "test_sheet_id")

            assert reader.credentials == mock_creds
            assert reader.sheet_id == "test_sheet_id"
            assert reader.service == mock_service
            mock_build.assert_called_once_with("sheets", "v4", credentials=mock_creds)

    @patch("fincli.sheets_connector.build")
    def test_read_all_rows_success(self, mock_build):
        """Test successful reading of all rows."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock the API response
        mock_response = {"values": [["Header1", "Header2"], ["Row1Col1", "Row1Col2"], ["Row2Col1", "Row2Col2"]]}
        mock_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = mock_response

        reader = SheetsReader(mock_creds, "test_sheet_id")
        rows = reader.read_all_rows("TestSheet")

        assert len(rows) == 3
        assert rows[0] == ["Header1", "Header2"]
        assert rows[1] == ["Row1Col1", "Row1Col2"]
        assert rows[2] == ["Row2Col1", "Row2Col2"]

    @patch("fincli.sheets_connector.build")
    def test_read_all_rows_empty(self, mock_build):
        """Test reading from empty sheet."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock empty response
        mock_response = {"values": []}
        mock_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = mock_response

        reader = SheetsReader(mock_creds, "test_sheet_id")
        rows = reader.read_all_rows("TestSheet")

        assert rows == []


class TestTaskParsing:
    """Test task parsing functionality."""

    def test_parse_task_data_valid(self):
        """Test parsing valid task data."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        reader = SheetsReader(mock_creds, "test_sheet_id")

        rows = [["Ts Time", "User Name", "Text", "Permalink", "RunID", "Source"], ["2025-01-15", "John Doe", "Test task", "http://example.com", "RUN001", "slack"], ["2025-01-16", "Jane Smith", "Another task", "http://example2.com", "RUN002", "email"]]

        tasks = reader.parse_task_data(rows)

        assert len(tasks) == 2
        assert tasks[0].remote_id == "RUN001"
        assert tasks[0].remote_source == "slack"
        assert "John Doe" in tasks[0].content
        assert "Test task" in tasks[0].content

    def test_parse_task_data_missing_required_columns(self):
        """Test parsing with missing required columns."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        reader = SheetsReader(mock_creds, "test_sheet_id")

        rows = [
            ["Ts Time", "User Name"],  # Missing RunID, Text, Source
        ]

        with pytest.raises(ValueError, match="Missing required columns"):
            reader.parse_task_data(rows)

    def test_parse_task_data_case_insensitive_headers(self):
        """Test parsing with case-insensitive headers."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        reader = SheetsReader(mock_creds, "test_sheet_id")

        rows = [["TS TIME", "USER NAME", "TEXT", "PERMALINK", "RUNID", "SOURCE"], ["2025-01-15", "John Doe", "Test task", "http://example.com", "RUN001", "slack"]]

        tasks = reader.parse_task_data(rows)

        assert len(tasks) == 1
        assert tasks[0].remote_id == "RUN001"
        assert "John Doe" in tasks[0].content

    def test_parse_task_data_skip_invalid_rows(self):
        """Test that invalid rows are skipped."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        reader = SheetsReader(mock_creds, "test_sheet_id")

        rows = [["Ts Time", "User Name", "Text", "Permalink", "RunID", "Source"], ["2025-01-15", "John Doe", "Test task", "http://example.com", "RUN001", "slack"], ["2025-01-16", "", "", "", "", "email"], ["2025-01-17", "Jane Smith", "Valid task", "http://example2.com", "RUN002", "email"]]  # Missing required fields

        tasks = reader.parse_task_data(rows)

        assert len(tasks) == 2  # Should skip the invalid row
        assert tasks[0].remote_id == "RUN001"
        assert tasks[1].remote_id == "RUN002"


class TestTaskFormatting:
    """Test task content formatting."""

    def test_format_task_content_complete(self):
        """Test formatting with all fields present."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        reader = SheetsReader(mock_creds, "test_sheet_id")

        from fincli.remote_models import RemoteTask, TaskAuthority

        task = RemoteTask(remote_id="TEST-001", remote_source="test_system", content="John Doe Test task description http://example.com")

        content = reader.format_task_content(task)

        assert content == "John Doe Test task description http://example.com"

    def test_format_task_content_missing_fields(self):
        """Test formatting with missing fields."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        reader = SheetsReader(mock_creds, "test_sheet_id")

        from fincli.remote_models import RemoteTask, TaskAuthority

        task = RemoteTask(remote_id="TEST-002", remote_source="test_system", content="John Doe Test task description")

        content = reader.format_task_content(task)

        assert content == "John Doe Test task description"

    def test_format_task_content_only_text(self):
        """Test formatting with only text field."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        reader = SheetsReader(mock_creds, "test_sheet_id")

        from fincli.remote_models import RemoteTask, TaskAuthority

        task = RemoteTask(remote_id="TEST-003", remote_source="test_system", content="Test task description")

        content = reader.format_task_content(task)

        assert content == "Test task description"

    def test_format_task_content_empty(self):
        """Test formatting with empty task."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        reader = SheetsReader(mock_creds, "test_sheet_id")

        from fincli.remote_models import RemoteTask, TaskAuthority

        task = RemoteTask(remote_id="TEST-004", remote_source="test_system", content="Minimal content")

        content = reader.format_task_content(task)

        assert content == "Minimal content"


class TestSheetInfo:
    """Test sheet information retrieval."""

    @patch("fincli.sheets_connector.build")
    def test_get_sheet_info(self, mock_build):
        """Test getting sheet information."""
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock the API response
        mock_response = {"properties": {"title": "Test Sheet"}, "sheets": [{"properties": {"title": "Sheet1", "sheetId": 123, "gridProperties": {"rowCount": 100, "columnCount": 10}}}]}
        mock_service.spreadsheets.return_value.get.return_value.execute.return_value = mock_response

        reader = SheetsReader(mock_creds, "test_sheet_id")
        sheet_info = reader.get_sheet_info()

        assert sheet_info["title"] == "Test Sheet"
        assert len(sheet_info["sheets"]) == 1
        assert sheet_info["sheets"][0]["name"] == "Sheet1"
        assert sheet_info["sheets"][0]["row_count"] == 100
        assert sheet_info["sheets"][0]["column_count"] == 10


if __name__ == "__main__":
    pytest.main([__file__])
