from datetime import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Request only what you need. Full read/write to Sheets:
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

CLIENT_SECRET_PATH = os.environ.get("GOOGLE_CLIENT_SECRET", "client_secret.json")
TOKEN_PATH = os.environ.get("GOOGLE_TOKEN_PATH", "token.json")


def get_credentials():
    """
    Runs a local OAuth flow (or refreshes an existing token), then
    saves token.json for future use. Returns google.oauth2.credentials.Credentials.
    """
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If no valid creds available, do the installed app flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh silently if we have a refresh token
            creds.refresh(Request())
        else:
            # Launch browser for user consent
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
            # Use local server flow (recommended for desktop). This opens a browser tab.
            creds = flow.run_local_server(port=0, prompt="consent")
        # Persist token for next time
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return creds


def print_credential_summary(creds: Credentials):
    print("\n✅ OAuth complete. Credentials ready.\n")
    print("Scopes:", ", ".join(creds.scopes or []))
    print("Has refresh token:", bool(creds.refresh_token))
    print("Access token (truncated):", (creds.token or "")[:20] + "…")
    print("Expiry (local time):", creds.expiry if creds.expiry else "Unknown")
    print("Saved to:", os.path.abspath(TOKEN_PATH))


def optional_sheets_ping(creds: Credentials):
    """
    Optional: If SHEET_ID is set, call the Sheets API to prove it works.
    Reads A1 from the first sheet.
    """
    sheet_id = os.environ.get("SHEET_ID")
    if not sheet_id:
        print("\n(ℹ️  Set SHEET_ID env var to test a real Sheets call, e.g.\n" "    export SHEET_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz\n" "    Then re-run this script.)")
        return

    try:
        service = build("sheets", "v4", credentials=creds)
        resp = service.spreadsheets().values().get(spreadsheetId=sheet_id, range="A1").execute()
        print("\n🧪 Sheets API call successful!")
        print("Sheet A1 value:", resp.get("values", [["(empty)"]])[0][0])
    except HttpError as e:
        print("\n⚠️  Sheets API call failed:")
        print(e)


if __name__ == "__main__":
    if not os.path.exists(CLIENT_SECRET_PATH):
        raise SystemExit(f"Could not find client secret at {CLIENT_SECRET_PATH}. " f"Set GOOGLE_CLIENT_SECRET or place client_secret.json next to this script.")

    creds = get_credentials()
    print_credential_summary(creds)
    optional_sheets_ping(creds)
