"""
Google Sheets Connector for FinCLI

Handles reading tasks from Google Sheets and converting them to local task format.
"""

from datetime import datetime
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:
    from .remote_models import RemoteSystemType, RemoteTask, RemoteTaskValidator, TaskAuthority, create_google_sheets_task
except ImportError:
    # For direct script execution
    from remote_models import RemoteSystemType, RemoteTask, RemoteTaskValidator, TaskAuthority, create_google_sheets_task

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SheetsReader:
    """Reads and parses data from Google Sheets."""

    def __init__(self, credentials: Credentials, sheet_id: str):
        """
        Initialize the sheets reader.

        Args:
            credentials: Google OAuth credentials
            sheet_id: Google Sheet ID
        """
        self.credentials = credentials
        self.sheet_id = sheet_id
        self.service = build("sheets", "v4", credentials=credentials)

    def read_all_rows(self, sheet_name: str = "Sheet1", max_rows: Optional[int] = None) -> List[List[str]]:
        """
        Read all rows from a specific sheet.

        Args:
            sheet_name: Name of the sheet to read (default: "Sheet1")
            max_rows: Optional maximum number of rows to read

        Returns:
            List of rows, where each row is a list of cell values
        """
        try:
            # Read all data from the sheet
            range_name = f"{sheet_name}!A:Z"  # Read columns A-Z
            result = self.service.spreadsheets().values().get(spreadsheetId=self.sheet_id, range=range_name).execute()

            values = result.get("values", [])
            if not values:
                logger.warning(f"No data found in sheet '{sheet_name}'")
                return []

            # Limit rows if max_rows is specified
            if max_rows and max_rows > 0:
                values = values[:max_rows]

            logger.info(f"Read {len(values)} rows from sheet '{sheet_name}'")
            return values

        except HttpError as e:
            logger.error(f"Error reading sheet '{sheet_name}': {e}")
            raise

    def read_rows_with_metadata(self, sheet_name: str = "Sheet1") -> List[Dict[str, Any]]:
        """
        Read rows with additional metadata including row numbers.

        Args:
            sheet_name: Name of the sheet to read

        Returns:
            List of dictionaries with row data and metadata
        """
        try:
            # Read all data from the sheet
            range_name = f"{sheet_name}!A:Z"  # Read columns A-Z
            result = self.service.spreadsheets().values().get(spreadsheetId=self.sheet_id, range=range_name).execute()

            values = result.get("values", [])
            if not values:
                logger.warning(f"No data found in sheet '{sheet_name}'")
                return []

            # Convert to list of dictionaries with metadata
            rows_with_metadata = []
            for i, row in enumerate(values, start=1):
                rows_with_metadata.append({"row_number": i, "data": row, "sheet_name": sheet_name})

            logger.info(f"Read {len(rows_with_metadata)} rows with metadata from sheet '{sheet_name}'")
            return rows_with_metadata

        except HttpError as e:
            logger.error(f"Error reading sheet '{sheet_name}' with metadata: {e}")
            raise

    def parse_task_data(self, rows: List[List[str]]) -> List[RemoteTask]:
        """
        Parse raw sheet rows into structured task data.

        Expected sheet structure:
        | Source | RunID | Ts Time | User Name | Text | Permalink |
        |--------|-------|---------|-----------|------|-----------|
        | ...    | ...   | ...     | ...       | ...  | ...       |

        Args:
            rows: Raw sheet rows from read_all_rows()

        Returns:
            List of parsed RemoteTask objects
        """
        if not rows:
            return []

        # Extract header row
        headers = rows[0]
        logger.info(f"Sheet headers: {headers}")

        # Expected column names (case-insensitive)
        expected_columns = {"source": ["source", "Source", "SOURCE"], "runid": ["runid", "RunID", "RUNID", "run_id"], "ts_time": ["ts time", "Ts Time", "TS TIME", "timestamp", "Timestamp"], "user_name": ["user name", "User Name", "USER NAME", "username", "Username"], "text": ["text", "Text", "TEXT", "description", "Description"], "permalink": ["permalink", "Permalink", "PERMALINK", "url", "URL", "link", "Link"]}

        # Find column indices
        column_indices = {}
        for col_name, possible_names in expected_columns.items():
            for possible_name in possible_names:
                if possible_name in headers:
                    column_indices[col_name] = headers.index(possible_name)
                    break
            if col_name not in column_indices:
                logger.warning(f"Required column '{col_name}' not found in headers: {headers}")

        # Check if we have all required columns
        required_columns = ["source", "runid", "user_name", "text"]
        missing_columns = [col for col in required_columns if col not in column_indices]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Parse data rows
        tasks = []
        for i, row in enumerate(rows[1:], start=2):  # Skip header row
            try:
                # Ensure row has enough columns
                while len(row) < max(column_indices.values()) + 1:
                    row.append("")

                # Extract task data
                source = row[column_indices["source"]].strip()
                runid = row[column_indices["runid"]].strip()
                user_name = row[column_indices["user_name"]].strip()
                text = row[column_indices["text"]].strip()
                permalink = row[column_indices.get("permalink", 0)].strip()

                # Validate required fields
                if not runid or not text:
                    logger.warning(f"Row {i}: Missing required fields (RunID or Text), skipping")
                    continue

                # Create remote task
                try:
                    remote_task = create_google_sheets_task(remote_id=runid, content="", user_name=user_name, text=text, permalink=permalink, source=source, remote_metadata={"row_number": i})  # Will be formatted by the factory function

                    # Validate the remote task
                    if RemoteTaskValidator.is_valid(remote_task):
                        tasks.append(remote_task)
                        logger.debug(f"Parsed task from row {i}: {runid}")
                    else:
                        errors = RemoteTaskValidator.validate_remote_task(remote_task)
                        logger.warning(f"Row {i}: Invalid remote task: {errors}")

                except Exception as e:
                    logger.error(f"Row {i}: Error creating remote task: {e}")
                    continue

            except Exception as e:
                logger.error(f"Error parsing row {i}: {e}")
                continue

        logger.info(f"Successfully parsed {len(tasks)} tasks from {len(rows)-1} data rows")
        return tasks

    def format_task_content(self, remote_task: RemoteTask) -> str:
        """
        Format remote task data into the required task content string.

        Args:
            remote_task: RemoteTask object

        Returns:
            Formatted task content string
        """
        # Use the content that was already formatted by the factory function
        return remote_task.content

    def get_sheet_info(self) -> Dict[str, Any]:
        """
        Get basic information about the sheet.

        Returns:
            Dictionary with sheet metadata
        """
        try:
            result = self.service.spreadsheets().get(spreadsheetId=self.sheet_id).execute()

            sheet_info = {"title": result.get("properties", {}).get("title", "Unknown"), "sheets": []}

            for sheet in result.get("sheets", []):
                sheet_props = sheet.get("properties", {})
                sheet_info["sheets"].append({"name": sheet_props.get("title", "Unknown"), "id": sheet_props.get("sheetId"), "row_count": sheet_props.get("gridProperties", {}).get("rowCount", 0), "column_count": sheet_props.get("gridProperties", {}).get("columnCount", 0)})

            return sheet_info

        except HttpError as e:
            logger.error(f"Error getting sheet info: {e}")
            raise

    def delete_row(self, sheet_name: str, row_number: int) -> bool:
        """
        Delete a specific row from a sheet.

        Args:
            sheet_name: Name of the sheet
            row_number: Row number to delete (1-based)

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Get sheet ID first
            sheet_info = self.get_sheet_info()
            sheet_id = None
            for sheet in sheet_info["sheets"]:
                if sheet["name"] == sheet_name:
                    sheet_id = sheet["id"]
                    break

            if sheet_id is None:
                logger.error(f"Sheet '{sheet_name}' not found")
                return False

            # Delete the row using the batchUpdate method
            request_body = {"requests": [{"deleteDimension": {"range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": row_number - 1, "endIndex": row_number}}}]}  # Convert to 0-based  # Delete single row

            self.service.spreadsheets().batchUpdate(spreadsheetId=self.sheet_id, body=request_body).execute()

            logger.info(f"Successfully deleted row {row_number} from sheet '{sheet_name}'")
            return True

        except HttpError as e:
            logger.error(f"Error deleting row {row_number} from sheet '{sheet_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting row {row_number} from sheet '{sheet_name}': {e}")
            return False

    def batch_delete_rows(self, sheet_name: str, row_numbers: List[int]) -> Dict[str, Any]:
        """
        Delete multiple rows from a sheet in a single batch operation.

        Args:
            sheet_name: Name of the sheet
            row_numbers: List of row numbers to delete (1-based)

        Returns:
            Dictionary with deletion results
        """
        if not row_numbers:
            return {"success": True, "deleted_rows": 0, "errors": []}

        try:
            # Get sheet ID first
            sheet_info = self.get_sheet_info()
            sheet_id = None
            for sheet in sheet_info["sheets"]:
                if sheet["name"] == sheet_name:
                    sheet_id = sheet["id"]
                    break

            if sheet_id is None:
                logger.error(f"Sheet '{sheet_name}' not found")
                return {"success": False, "deleted_rows": 0, "errors": [f"Sheet '{sheet_name}' not found"]}

            # Sort row numbers in descending order to avoid index shifting issues
            sorted_row_numbers = sorted(row_numbers, reverse=True)

            # Create batch delete requests
            requests = []
            for row_number in sorted_row_numbers:
                requests.append({"deleteDimension": {"range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": row_number - 1, "endIndex": row_number}}})  # Convert to 0-based  # Delete single row

            request_body = {"requests": requests}

            self.service.spreadsheets().batchUpdate(spreadsheetId=self.sheet_id, body=request_body).execute()

            logger.info(f"Successfully deleted {len(sorted_row_numbers)} rows from sheet '{sheet_name}'")
            return {"success": True, "deleted_rows": len(sorted_row_numbers), "deleted_row_numbers": sorted_row_numbers, "errors": []}

        except HttpError as e:
            error_msg = f"Error batch deleting rows from sheet '{sheet_name}': {e}"
            logger.error(error_msg)
            return {"success": False, "deleted_rows": 0, "errors": [error_msg]}
        except Exception as e:
            error_msg = f"Unexpected error batch deleting rows from sheet '{sheet_name}': {e}"
            logger.error(error_msg)
            return {"success": False, "deleted_rows": 0, "errors": [error_msg]}


def create_sheets_reader_from_token(token_path: str, sheet_id: str) -> SheetsReader:
    """
    Create a SheetsReader instance from a saved token file.

    Args:
        token_path: Path to the token.json file
        sheet_id: Google Sheet ID

    Returns:
        SheetsReader instance
    """
    if not os.path.exists(token_path):
        raise FileNotFoundError(f"Token file not found: {token_path}")

    credentials = Credentials.from_authorized_user_file(token_path, ["https://www.googleapis.com/auth/spreadsheets"])

    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            raise ValueError("Invalid or expired credentials")

    return SheetsReader(credentials, sheet_id)


def test_sheets_connector():
    """Test function for the sheets connector."""
    sheet_id = os.environ.get("SHEET_ID")
    if not sheet_id:
        print("❌ SHEET_ID environment variable not set")
        print("Set it with: export SHEET_ID=your_sheet_id_here")
        return

    token_path = os.environ.get("GOOGLE_TOKEN_PATH", "token.json")
    if not os.path.exists(token_path):
        print(f"❌ Token file not found: {token_path}")
        print("Run gcreds.py first to authenticate")
        return

    try:
        # Create reader
        reader = create_sheets_reader_from_token(token_path, sheet_id)
        print(f"✅ Connected to sheet: {sheet_id}")

        # Get sheet info
        sheet_info = reader.get_sheet_info()
        print(f"📊 Sheet: {sheet_info['title']}")
        print(f"📋 Sheets: {[s['name'] for s in sheet_info['sheets']]}")

        # Read and parse data
        for sheet in sheet_info["sheets"]:
            sheet_name = sheet["name"]
            print(f"\n📖 Reading sheet: {sheet_name}")

            rows = reader.read_all_rows(sheet_name)
            if rows:
                try:
                    tasks = reader.parse_task_data(rows)
                    print(f"📝 Found {len(tasks)} tasks")

                    # Show first few tasks
                    for i, task in enumerate(tasks[:3]):
                        print(f"  {i+1}. {task.content}")
                        print(f"      Remote ID: {task.remote_id}")
                        print(f"      Authority: {task.authority.value}")
                        print(f"      Shadow: {task.is_shadow_task}")

                    if len(tasks) > 3:
                        print(f"  ... and {len(tasks) - 3} more tasks")

                except ValueError as e:
                    print(f"⚠️  Skipping sheet '{sheet_name}': {e}")
                    continue
                except Exception as e:
                    print(f"❌ Error processing sheet '{sheet_name}': {e}")
                    continue

    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Detailed error information")


if __name__ == "__main__":
    test_sheets_connector()
