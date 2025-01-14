import typer
from typing_extensions import Annotated
from pathlib import Path
from importlib.util import find_spec
import subprocess

from budgetmoney.utils.data import (
    update_master_transaction_df,
    load_master_transaction_df,
)
from budgetmoney.utils.gcloud import GSheetsClient


import os
from dotenv import load_dotenv

load_dotenv

app = typer.Typer()


@app.command()
def launch(data_dir: str):
    if not Path(data_dir).exists():
        raise Exception(f"The data dir: '{data_dir}' does not exist!")
    app_location = find_spec("budgetmoney.app.app").origin
    subprocess.run(["streamlit", "run", app_location, "--", f"{data_dir}"])


@app.command()
def update(
    data_dir: str,
    validate: Annotated[
        bool,
        typer.Option(
            help="Ensure that master transaction file has all necessary cols and features."
        ),
    ] = False,
):
    if not Path(data_dir).exists():
        raise Exception(f"The data dir: '{data_dir}' does not exist!")
    if validate:
        load_master_transaction_df(data_dir, validate=True)
    response = update_master_transaction_df(data_dir, return_df=False, return_msg=True)
    print(response)


@app.command()
def sync(data_dir: str):
    if not Path(data_dir).exists():
        raise Exception(f"The data dir: '{data_dir}' does not exist!")
    df = load_master_transaction_df(data_dir)
    gs_client = GSheetsClient(
        sheet_id=os.getenv("SPREADSHEET_ID"),
        sa_cred_path=os.getenv("GCP_SERVICE_ACCOUNT_PATH"),
    )

    response = gs_client.sync_sheet(df=df, sheet_name=os.getenv("SPREADSHEET_TAB_NAME"))
    if response["status"] == 1:
        print("Successfully synced gsheet!")
    else:
        print(f"Sync Error!\n{response["message"]}")


if __name__ == "__main__":
    app()
