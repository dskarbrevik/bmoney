from googleapiclient.discovery import build
from google.oauth2 import service_account

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from pathlib import Path


class GSheetsClient:
    """Simple Google Sheets client to get and set data in a spreadsheet."""

    def __init__(
        self, sheet_id: str, sa_cred_path: str = None, oauth_secret_path: str = None
    ):
        """
        Args:
            sheet_id (str): ID of gsheet of interest
            sa_cred_path (str, optional): SA cred json path. Must set this OR oauth_secret_path parameter. Defaults to None.
            oauth_secret_path (str, optional): oauth secret json path. Must set this OR sa_cred_path parameter. Defaults to None.

        Raises:
            Exception: _description_
        """
        self.sheet_id = sheet_id
        if not sa_cred_path and not oauth_secret_path:
            raise Exception(
                "Must provide either an sa_cred_path or oauth_secret_path to access Gsheet features."
            )
        self.sa_cred_path = sa_cred_path
        self.oauth_secret_path = oauth_secret_path
        self._authenticate()
        self.service = build("sheets", "v4", credentials=self.creds)

    def _reauth(self):
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())

    def _authenticate(self):
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

        # SA auth
        if self.sa_cred_path:
            self.creds = service_account.Credentials.from_service_account_file(
                self.sa_cred_path, scopes=SCOPES
            )
        # User auth
        else:
            user_cred_path = (
                Path(self.oauth_secret_path)
                .parent.joinpath("token.json")
                .resolve()
                .as_posix()
            )
            if Path(user_cred_path).exists():
                self.creds = Credentials.from_authorized_user_file(
                    user_cred_path, SCOPES
                )
                if not self.creds.valid():
                    self._reauth()
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.oauth_secret_path, SCOPES
                )
                self.creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open(user_cred_path, "w") as token:
                    token.write(self.creds.to_json())

    def read_data(self, sheet_range):
        # Call the Sheets API
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.sheet_id, range=sheet_range)
            .execute()
        )
        values = result.get("values", [])
        if not values:
            print("No data found.")
        return values

    def update_data(self, sheet_range, values):
        body = {"values": values}
        # Update the cells
        result = (
            self.service.spreadsheets()
            .values()
            .update(
                spreadsheetId=self.sheet_id,
                range=sheet_range,
                valueInputOption="RAW",  # Use 'RAW' or 'USER_ENTERED'
                body=body,
            )
            .execute()
        )

        print(f"{result.get('updatedCells')} cells updated.")

    def append_data(self, sheet_range, values):
        body = {"values": values}
        # Update the cells
        result = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.sheet_id,
                range=sheet_range,
                valueInputOption="RAW",  # Use 'RAW' or 'USER_ENTERED'
                body=body,
            )
            .execute()
        )

        print(f"{result.get('updatedCells')} cells updated.")
