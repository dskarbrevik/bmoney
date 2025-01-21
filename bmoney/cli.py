import typer
from typing_extensions import Annotated
from pathlib import Path
from importlib.util import find_spec
import subprocess

from bmoney.utils.data import (
    update_master_transaction_df,
    load_master_transaction_df,
)
from bmoney.utils.gcloud import GSheetsClient
from bmoney.utils.config import create_config_file, load_config_file, save_config_file
from bmoney.constants import (
    MASTER_DF_FILENAME,
    MASTER_COLUMNS,
    CONFIG_JSON_FILENAME,
)
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv

app = typer.Typer()


@app.command()
def init(
    username: Annotated[str, typer.Option(prompt=True)],
    path: str = ".",
    no_update: bool = False,
):
    config_path_root = Path(path)
    if not config_path_root.exists():
        raise Exception(
            f"The path: '{config_path_root.resolve().as_posix()}' does not exist!"
        )

    config_path_json = Path(config_path_root / CONFIG_JSON_FILENAME)
    if not config_path_json.exists():
        create_config_file()

    config = load_config_file()  # get user config
    config["BUDGET_MONEY_USER"] = username
    save_config_file(config=config)
    config_path_df = Path(
        config_path_root / config.get("MASTER_DF_FILENAME", MASTER_DF_FILENAME)
    )
    if not config_path_df.exists():
        df = pd.DataFrame(columns=config.get("MASTER_COLUMNS", MASTER_COLUMNS))
        df.to_json(config_path_df, orient="records", lines=True)
        if not no_update:
            update_master_transaction_df(config_path_root)
    else:
        print("Master transaction file found... skipping.")


@app.command()
def launch(data_dir: str = "."):
    if not Path(data_dir).exists():
        raise Exception(f"The data dir: '{data_dir}' does not exist!")
    app_location = find_spec("bmoney.app.app").origin
    subprocess.run(["streamlit", "run", app_location, "--", f"{data_dir}"])


@app.command()
def update(
    data_dir: str = ".",
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
def sync(data_dir: str = "."):
    config = load_config_file()
    if not Path(data_dir).exists():
        print(f"ERROR: The data dir: '{data_dir}' does not exist!")
        return
    df = load_master_transaction_df(data_dir)

    spreadsheet_id = config.get("GSHEETS_CONFIG").get("SPREADSHEET_ID") or os.getenv(
        "SPREADSHEET_ID"
    )
    if not spreadsheet_id:
        print(
            "ERROR: Your config.json file is missing a 'SPREADSHEET_ID' value in the 'GSHEETS_CONFIG' section."
        )
        return
    gcp_service_account_path = config.get("GSHEETS_CONFIG").get(
        "GCP_SERVICE_ACCOUNT_PATH"
    ) or os.getenv("GCP_SERVICE_ACCOUNT_PATH")
    if not gcp_service_account_path:
        print(
            "ERROR: Your config.json file is missing a 'GCP_SERVICE_ACCOUNT_PATH' value in the 'GSHEETS_CONFIG' section."
        )
        return
    gs_client = GSheetsClient(
        sheet_id=spreadsheet_id,
        sa_cred_path=gcp_service_account_path,
    )
    sheet_name = config.get("GSHEETS_CONFIG").get("SPREADSHEET_TAB_NAME") or os.getenv(
        "SPREADSHEET_TAB_NAME"
    )
    if not sheet_name:
        print(
            "ERROR: Your config.json file is missing a 'SPREADSHEET_TAB_NAME' value in the 'GSHEETS_CONFIG' section."
        )
    response = gs_client.sync_sheet(df=df, sheet_name=sheet_name)
    if response["status"] == 1:
        print("Successfully synced gsheet!")
    else:
        print(f"Sync Error!\n{response['message']}")


if __name__ == "__main__":
    app()
