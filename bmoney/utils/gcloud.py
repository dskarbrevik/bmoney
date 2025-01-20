from googleapiclient.discovery import build
from google.oauth2 import service_account

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from bmoney.utils.data import monthly_gsheets_cost_table

from pathlib import Path
import pandas as pd


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

    def clear_data(self, sheet_range):
        result = (
            self.service.spreadsheets()
            .values()
            .clear(spreadsheetId=self.sheet_id, range=sheet_range)
            .execute()
        )
        return result

    def read_data(self, sheet_range):
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

        return f"{result.get('updatedCells')} cells updated."

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

        return f"{result.get('updatedCells')} cells updated."

    def sync_sheet(self, df: pd.DataFrame, sheet_name: str) -> dict:
        """Takes a transaction dataframe and gsheet range to ensure the sheet is up to date with the dataframe.

        Args:
            df (pd.DataFrame): transaction dataframe
            sheet_name (str): name of the tab/sheet in your spreadsheet

        Returns:
            dict: keys - "status","message"
        """

        try:
            # get data for gsheets from master transaction
            values = monthly_gsheets_cost_table(
                df, only_shared=True, return_values=True
            )
            end_range = df.shape[1]
            sheet_range = f"{sheet_name}!A:{chr(64 + end_range)}"

            # ATTEMPT AT MERGING DATA INSTEAD OF REPLACING AS IS CURRENT APPROACH
            # BUT RESULTS IN WEIRD DUPLICATE ROW BEHAVIORS IN SPREADSHEET
            # old_data = self.read_data(sheet_range=sheet_range)
            # if old_data:
            #     old_df = pd.DataFrame(old_data[1:],columns=old_data[0])
            #     assert all(cat_df.columns==old_df.columns)
            #     if not old_df.empty:
            #         old_df["Amount"] = old_df["Amount"].astype(float).round(2)
            #         old_df = old_df[old_df["Category"].isin(SHARED_EXPENSES)]
            #         new_df = pd.concat([cat_df,old_df])
            #         new_df = new_df.drop_duplicates()
            #         # new_df = new_df[new_df["Category"].isin(SHARED_EXPENSES)]
            #         values = [new_df.columns.tolist()] + new_df.values.tolist()

            self.clear_data(sheet_range=sheet_range)
            response = self.update_data(sheet_range=sheet_range, values=values)
            return {"status": 1, "message": response}
        except Exception as e:
            return {"status": 0, "message": e}
