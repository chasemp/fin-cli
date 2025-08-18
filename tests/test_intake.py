"""
Tests for the intake module.
"""

import tempfile
from unittest.mock import mock_open, patch

import pytest

from fincli.intake import get_available_sources, import_from_source


class TestIntakeModule:
    """Test the intake module functionality."""

    def test_get_available_sources(self):
        """Test getting available import sources."""
        sources = get_available_sources()

        expected_sources = ["csv", "json", "text", "sheets", "excel"]
        assert set(sources) == set(expected_sources)

    def test_import_from_source_valid_source(self):
        """Test importing from a valid source."""
        with patch("fincli.intake.SOURCES") as mock_sources:

            def mock_importer(**kwargs):
                return {"imported": 5, "errors": []}

            mock_sources.__contains__.return_value = True
            mock_sources.__getitem__.return_value = mock_importer

            result = import_from_source("csv", file_path="test.csv")

            assert result == {"imported": 5, "errors": []}
            mock_sources.__getitem__.assert_called_once_with("csv")

    def test_import_from_source_invalid_source(self):
        """Test importing from an invalid source."""
        with pytest.raises(ValueError, match="Unknown source: invalid"):
            import_from_source("invalid", file_path="test.txt")

    def test_import_from_source_passes_kwargs(self):
        """Test that kwargs are passed to the importer function."""
        with patch("fincli.intake.SOURCES") as mock_sources:

            def mock_importer(**kwargs):
                return kwargs

            mock_sources.__contains__.return_value = True
            mock_sources.__getitem__.return_value = mock_importer

            result = import_from_source("json", file_path="test.json", encoding="utf-8")

            assert result["file_path"] == "test.json"
            assert result["encoding"] == "utf-8"


class TestCSVImporter:
    """Test CSV import functionality."""

    def test_csv_import_integration(self):
        """Test CSV import integration."""
        with patch("fincli.intake.import_csv_tasks") as mock_csv_import:
            mock_csv_import.return_value = {"imported": 3, "errors": []}

            with patch("fincli.intake.SOURCES") as mock_sources:
                mock_sources.__contains__.return_value = True
                mock_sources.__getitem__.return_value = mock_csv_import

                result = import_from_source("csv", file_path="test.csv")

                assert result["imported"] == 3
                assert result["errors"] == []
                mock_csv_import.assert_called_once_with(file_path="test.csv")


class TestJSONImporter:
    """Test JSON import functionality."""

    def test_json_import_integration(self):
        """Test JSON import integration."""
        with patch("fincli.intake.import_json_tasks") as mock_json_import:
            mock_json_import.return_value = {"imported": 2, "errors": []}

            with patch("fincli.intake.SOURCES") as mock_sources:
                mock_sources.__contains__.return_value = True
                mock_sources.__getitem__.return_value = mock_json_import

                result = import_from_source("json", file_path="test.json")

                assert result["imported"] == 2
                assert result["errors"] == []
                mock_json_import.assert_called_once_with(file_path="test.json")


class TestTextImporter:
    """Test text import functionality."""

    def test_text_import_integration(self):
        """Test text import integration."""
        with patch("fincli.intake.import_text_tasks") as mock_text_import:
            mock_text_import.return_value = {"imported": 4, "errors": []}

            with patch("fincli.intake.SOURCES") as mock_sources:
                mock_sources.__contains__.return_value = True
                mock_sources.__getitem__.return_value = mock_text_import

                result = import_from_source("text", file_path="test.txt")

                assert result["imported"] == 4
                assert result["errors"] == []
                mock_text_import.assert_called_once_with(file_path="test.txt")


class TestSheetsImporter:
    """Test Google Sheets import functionality."""

    def test_sheets_import_integration(self):
        """Test Google Sheets import integration."""
        with patch("fincli.intake.import_sheets_tasks") as mock_sheets_import:
            mock_sheets_import.return_value = {"imported": 1, "errors": []}

            with patch("fincli.intake.SOURCES") as mock_sources:
                mock_sources.__contains__.return_value = True
                mock_sources.__getitem__.return_value = mock_sheets_import

                result = import_from_source("sheets", sheet_id="test_sheet_id")

                assert result["imported"] == 1
                assert result["errors"] == []
                mock_sheets_import.assert_called_once_with(sheet_id="test_sheet_id")


class TestExcelImporter:
    """Test Excel import functionality."""

    def test_excel_import_integration(self):
        """Test Excel import integration."""
        with patch("fincli.intake.import_excel_tasks") as mock_excel_import:
            mock_excel_import.return_value = {"imported": 6, "errors": []}

            with patch("fincli.intake.SOURCES") as mock_sources:
                mock_sources.__contains__.return_value = True
                mock_sources.__getitem__.return_value = mock_excel_import

                result = import_from_source("excel", file_path="test.xlsx")

                assert result["imported"] == 6
                assert result["errors"] == []
                mock_excel_import.assert_called_once_with(file_path="test.xlsx")


class TestImportErrorHandling:
    """Test error handling in import functions."""

    def test_import_from_source_with_errors(self):
        """Test import with errors."""
        with patch("fincli.intake.SOURCES") as mock_sources:

            def mock_importer(**kwargs):
                return {"imported": 0, "errors": ["File not found"]}

            mock_sources.__contains__.return_value = True
            mock_sources.__getitem__.return_value = mock_importer

            result = import_from_source("csv", file_path="nonexistent.csv")

            assert result["imported"] == 0
            assert result["errors"] == ["File not found"]

    def test_import_from_source_importer_exception(self):
        """Test import when importer raises an exception."""
        with patch("fincli.intake.SOURCES") as mock_sources:

            def mock_importer(**kwargs):
                raise FileNotFoundError("File not found")

            mock_sources.__contains__.return_value = True
            mock_sources.__getitem__.return_value = mock_importer

            with pytest.raises(FileNotFoundError):
                import_from_source("csv", file_path="nonexistent.csv")


class TestImportSourceValidation:
    """Test validation of import sources."""

    def test_all_sources_are_callable(self):
        """Test that all sources in SOURCES are callable functions."""
        from fincli.intake import SOURCES

        for source_name, source_func in SOURCES.items():
            assert callable(source_func), f"Source {source_name} is not callable"

    def test_source_names_are_strings(self):
        """Test that all source names are strings."""
        from fincli.intake import SOURCES

        for source_name in SOURCES.keys():
            assert isinstance(source_name, str), f"Source name {source_name} is not a string"
