"""
Tests for enhanced SheetsReader functionality.
"""

from unittest.mock import MagicMock, Mock, call, patch

from googleapiclient.errors import HttpError
import pytest

from fincli.sheets_connector import SheetsReader


class TestSheetsReaderEnhanced:
    """Test enhanced SheetsReader functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_credentials = Mock()
        self.sheet_id = "test_sheet_id"
        self.mock_service = Mock()

        # Set up the mock service chain properly
        self.mock_spreadsheets = Mock()
        self.mock_service.spreadsheets.return_value = self.mock_spreadsheets

        # Patch the build function to return our mock service
        with patch("fincli.sheets_connector.build") as mock_build:
            mock_build.return_value = self.mock_service
            self.reader = SheetsReader(self.mock_credentials, self.sheet_id)

        # Ensure the mock service is properly attached to the reader
        self.reader.service = self.mock_service

    def _setup_mock_get(self, mock_sheet_info):
        """Helper method to set up mock get chain."""
        mock_get = Mock()
        mock_get.execute.return_value = mock_sheet_info
        # The get method is called with spreadsheetId parameter, so we need to handle that
        # Use side_effect to ensure the mock is called regardless of parameters
        self.mock_spreadsheets.get.side_effect = lambda *args, **kwargs: mock_get
        return mock_get

    def _setup_mock_values_get(self, mock_values):
        """Helper method to set up mock values().get() chain for read operations."""
        mock_values_obj = Mock()
        mock_values_obj.get.return_value = Mock()
        mock_values_obj.get.return_value.execute.return_value = {"values": mock_values}
        self.mock_spreadsheets.values.return_value = mock_values_obj
        return mock_values_obj

    def _setup_mock_batch_update(self, return_value=None, side_effect=None):
        """Helper method to set up mock batchUpdate chain."""
        mock_batch_update = Mock()
        if side_effect:
            mock_batch_update.execute.side_effect = side_effect
        else:
            mock_batch_update.execute.return_value = return_value
        self.mock_spreadsheets.batchUpdate.return_value = mock_batch_update
        return mock_batch_update

    def test_read_all_rows_with_max_rows(self):
        """Test read_all_rows with max_rows parameter."""
        mock_values = [["Header1", "Header2"], ["Row1Col1", "Row1Col2"], ["Row2Col1", "Row2Col2"], ["Row3Col1", "Row3Col2"]]

        self._setup_mock_values_get(mock_values)

        # Test with max_rows limit
        result = self.reader.read_all_rows("test_sheet", max_rows=2)

        assert len(result) == 2
        assert result == mock_values[:2]

        # Test without max_rows (should read all)
        result = self.reader.read_all_rows("test_sheet")
        assert len(result) == 4
        assert result == mock_values

    def test_read_all_rows_empty_sheet(self):
        """Test read_all_rows with empty sheet."""
        self._setup_mock_values_get([])

        result = self.reader.read_all_rows("test_sheet", max_rows=5)

        assert result == []
        assert len(result) == 0

    def test_read_rows_with_metadata(self):
        """Test read_rows_with_metadata method."""
        mock_values = [["Header1", "Header2"], ["Row1Col1", "Row1Col2"], ["Row2Col1", "Row2Col2"]]

        self._setup_mock_values_get(mock_values)

        result = self.reader.read_rows_with_metadata("test_sheet")

        assert len(result) == 3

        # Check header row
        assert result[0]["row_number"] == 1
        assert result[0]["data"] == ["Header1", "Header2"]
        assert result[0]["sheet_name"] == "test_sheet"

        # Check first data row
        assert result[1]["row_number"] == 2
        assert result[1]["data"] == ["Row1Col1", "Row1Col2"]
        assert result[1]["sheet_name"] == "test_sheet"

    def test_read_rows_with_metadata_empty_sheet(self):
        """Test read_rows_with_metadata with empty sheet."""
        self._setup_mock_values_get([])

        result = self.reader.read_rows_with_metadata("test_sheet")

        assert result == []
        assert len(result) == 0

    def test_delete_row_success(self):
        """Test successful row deletion."""
        # Mock sheet info - needs to match Google Sheets API response format
        mock_sheet_info = {"properties": {"title": "Test Sheet"}, "sheets": [{"properties": {"title": "test_sheet", "sheetId": 123, "gridProperties": {"rowCount": 100, "columnCount": 10}}}]}

        # Mock successful deletion
        mock_delete_result = {"replies": [{"deleteDimension": {}}]}

        # Set up the mock chain properly
        self._setup_mock_get(mock_sheet_info)
        self._setup_mock_batch_update(mock_delete_result)

        result = self.reader.delete_row("test_sheet", 5)

        assert result is True

        # Verify the correct API calls were made
        self.mock_spreadsheets.get.assert_called_once_with(spreadsheetId=self.sheet_id)

        # Verify batchUpdate was called with correct parameters
        batch_update_call = self.mock_spreadsheets.batchUpdate.call_args
        assert batch_update_call[1]["spreadsheetId"] == self.sheet_id

        request_body = batch_update_call[1]["body"]
        assert "requests" in request_body
        assert len(request_body["requests"]) == 1

        delete_request = request_body["requests"][0]["deleteDimension"]
        assert delete_request["range"]["sheetId"] == 123
        assert delete_request["range"]["startIndex"] == 4  # 5-1 (0-based)
        assert delete_request["range"]["endIndex"] == 5

    def test_delete_row_sheet_not_found(self):
        """Test row deletion when sheet is not found."""
        mock_sheet_info = {"properties": {"title": "Test Sheet"}, "sheets": [{"properties": {"title": "other_sheet", "sheetId": 123, "gridProperties": {"rowCount": 100, "columnCount": 10}}}]}

        self._setup_mock_get(mock_sheet_info)

        result = self.reader.delete_row("test_sheet", 5)

        assert result is False

    def test_delete_row_api_error(self):
        """Test row deletion with API error."""
        # Mock sheet info - needs to match Google Sheets API response format
        mock_sheet_info = {"properties": {"title": "Test Sheet"}, "sheets": [{"properties": {"title": "test_sheet", "sheetId": 123, "gridProperties": {"rowCount": 100, "columnCount": 10}}}]}

        # Mock API error
        self._setup_mock_get(mock_sheet_info)
        self._setup_mock_batch_update(side_effect=HttpError(Mock(status=403), b"Quota exceeded"))

        result = self.reader.delete_row("test_sheet", 5)

        assert result is False

    def test_batch_delete_rows_success(self):
        """Test successful batch row deletion."""
        # Mock sheet info - needs to match Google Sheets API response format
        mock_sheet_info = {"properties": {"title": "Test Sheet"}, "sheets": [{"properties": {"title": "test_sheet", "sheetId": 123, "gridProperties": {"rowCount": 100, "columnCount": 10}}}]}

        # Mock successful deletion
        mock_delete_result = {"replies": [{"deleteDimension": {}}] * 3}

        self._setup_mock_get(mock_sheet_info)
        self._setup_mock_batch_update(mock_delete_result)

        result = self.reader.batch_delete_rows("test_sheet", [5, 10, 15])

        assert result["success"] is True
        assert result["deleted_rows"] == 3
        assert result["deleted_row_numbers"] == [15, 10, 5]  # Should be sorted descending
        assert result["errors"] == []

        # Verify batchUpdate was called with correct parameters
        batch_update_call = self.mock_spreadsheets.batchUpdate.call_args
        request_body = batch_update_call[1]["body"]

        # Should have 3 delete requests
        assert len(request_body["requests"]) == 3

        # Verify the requests are in descending order (to avoid index shifting)
        first_request = request_body["requests"][0]["deleteDimension"]["range"]
        assert first_request["startIndex"] == 14  # 15-1 (0-based)
        assert first_request["endIndex"] == 15

    def test_batch_delete_rows_empty_list(self):
        """Test batch deletion with empty row list."""
        result = self.reader.batch_delete_rows("test_sheet", [])

        assert result["success"] is True
        assert result["deleted_rows"] == 0
        assert result["errors"] == []

        # Should not make any API calls
        self.mock_spreadsheets.get.assert_not_called()
        self.mock_spreadsheets.batchUpdate.assert_not_called()

    def test_batch_delete_rows_sheet_not_found(self):
        """Test batch deletion when sheet is not found."""
        mock_sheet_info = {"properties": {"title": "Test Sheet"}, "sheets": [{"properties": {"title": "other_sheet", "sheetId": 123, "gridProperties": {"rowCount": 100, "columnCount": 10}}}]}

        self._setup_mock_get(mock_sheet_info)

        result = self.reader.batch_delete_rows("test_sheet", [5, 10])

        assert result["success"] is False
        assert result["deleted_rows"] == 0
        assert len(result["errors"]) == 1
        assert "not found" in result["errors"][0]

    def test_batch_delete_rows_api_error(self):
        """Test batch deletion with API error."""
        # Mock sheet info - needs to match Google Sheets API response format
        mock_sheet_info = {"properties": {"title": "Test Sheet"}, "sheets": [{"properties": {"title": "test_sheet", "sheetId": 123, "gridProperties": {"rowCount": 100, "columnCount": 10}}}]}

        # Mock API error
        self._setup_mock_get(mock_sheet_info)
        self._setup_mock_batch_update(side_effect=HttpError(Mock(status=429), b"Rate limit exceeded"))

        result = self.reader.batch_delete_rows("test_sheet", [5, 10])

        assert result["success"] is False
        assert result["deleted_rows"] == 0
        assert len(result["errors"]) == 1
        assert "Rate limit exceeded" in result["errors"][0]

    def test_batch_delete_rows_unexpected_error(self):
        """Test batch deletion with unexpected error."""
        # Mock sheet info - needs to match Google Sheets API response format
        mock_sheet_info = {"properties": {"title": "Test Sheet"}, "sheets": [{"properties": {"title": "test_sheet", "sheetId": 123, "gridProperties": {"rowCount": 100, "columnCount": 10}}}]}

        # Mock unexpected error
        self._setup_mock_get(mock_sheet_info)
        self._setup_mock_batch_update(side_effect=Exception("Network error"))

        result = self.reader.batch_delete_rows("test_sheet", [5, 10])

        assert result["success"] is False
        assert result["deleted_rows"] == 0
        assert len(result["errors"]) == 1
        assert "Network error" in result["errors"][0]

    def test_delete_row_index_calculation(self):
        """Test that row indices are correctly calculated (1-based to 0-based conversion)."""
        # Mock sheet info - needs to match Google Sheets API response format
        mock_sheet_info = {"properties": {"title": "Test Sheet"}, "sheets": [{"properties": {"title": "test_sheet", "sheetId": 123, "gridProperties": {"rowCount": 100, "columnCount": 10}}}]}

        # Mock successful deletion
        mock_delete_result = {"replies": [{"deleteDimension": {}}]}

        self._setup_mock_get(mock_sheet_info)
        self._setup_mock_batch_update(mock_delete_result)

        # Delete row 1 (should become index 0)
        self.reader.delete_row("test_sheet", 1)

        batch_update_call = self.mock_spreadsheets.batchUpdate.call_args
        request_body = batch_update_call[1]["body"]
        delete_request = request_body["requests"][0]["deleteDimension"]["range"]

        assert delete_request["startIndex"] == 0  # 1-1 = 0
        assert delete_request["endIndex"] == 1

        # Delete row 10 (should become index 9)
        self.reader.delete_row("test_sheet", 10)

        batch_update_call = self.mock_spreadsheets.batchUpdate.call_args
        request_body = batch_update_call[1]["body"]
        delete_request = request_body["requests"][0]["deleteDimension"]["range"]

        assert delete_request["startIndex"] == 9  # 10-1 = 9
        assert delete_request["endIndex"] == 10
