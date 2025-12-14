import typer
from typing_extensions import Annotated
from typing import Optional
from pathlib import Path
from importlib.util import find_spec
import subprocess

from bmoney.utils.data import (
    update_master_transaction_df,
    load_master_transaction_df,
    save_master_transaction_df,
    backup_master_transaction_df,
)
from bmoney.utils.deduplication import deduplicate_transactions
from bmoney.utils.gcloud import GSheetsClient
from bmoney.utils.config import (
    create_config_file,
    load_config_file,
    save_config_file,
    update_config_file,
)
from bmoney.constants import (
    MASTER_DF_FILENAME,
    MASTER_COLUMNS,
    CONFIG_JSON_FILENAME,
    DEFAULT_CONFIG,
    CURRENT_VERSION,
)
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv


def version_callback(value: bool):
    if value:
        typer.echo(f"{CURRENT_VERSION}")
        raise typer.Exit()


app = typer.Typer()
db_app = typer.Typer()
app.add_typer(db_app, name="db")
config_app = typer.Typer()
app.add_typer(config_app, name="config")
gsheets_app = typer.Typer()
app.add_typer(gsheets_app, name="gsheets")


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
):
    """
    bmoney - Budget Money transaction management CLI
    """
    pass


@app.command("init")
def app_init(
    username: Annotated[str, typer.Option(prompt=True)],
    path: str = ".",
    no_update: bool = False,
    force: bool = False,
):
    config_path_root = Path(path)
    if not config_path_root.exists():
        raise Exception(
            f"The path: '{config_path_root.resolve().as_posix()}' does not exist!"
        )

    config_path_json = Path(config_path_root / CONFIG_JSON_FILENAME)
    if not config_path_json.exists():
        create_config_file(path=path)
    elif not force:
        raise Exception(
            "This looks like an active project dir. Config file already exists... use --force to overwrite."
        )
    else:
        print("Config found, but force flag used... updating config file.")

    config = load_config_file()  # get user config
    if config.get("CONFIG_VERSION") != DEFAULT_CONFIG.get("CONFIG_VERSION"):
        config = update_config_file(config=config)
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
        print("Master transaction file already found... skipping creation.")


@app.command("launch")
def app_launch(data_dir: str = "."):
    if not Path(data_dir).exists():
        raise Exception(f"The data dir: '{data_dir}' does not exist!")
    app_location = find_spec("bmoney.app.app").origin
    subprocess.run(["streamlit", "run", app_location, "--", f"{data_dir}"])


@db_app.command("update")
def db_update(
    data_dir: str = ".",
    validate: Annotated[
        bool,
        typer.Option(
            help="Ensure that master transaction file has all necessary cols and features."
        ),
    ] = False,
    smart_categories: Annotated[
        Optional[bool],
        typer.Option(
            help="Use smart categorization based on historical transaction names. If not specified, uses config.json setting (default: True)."
        ),
    ] = None,
):
    if not Path(data_dir).exists():
        raise Exception(f"The data dir: '{data_dir}' does not exist!")
    if validate:
        load_master_transaction_df(data_dir, validate=True)
    response = update_master_transaction_df(
        data_dir, return_df=False, return_msg=True, smart_categories=smart_categories
    )
    print(response)


@db_app.command("dedup")
def db_dedup(
    data_dir: str = ".",
    date_window: Annotated[
        int,
        typer.Option(
            help="Number of days to look for potential duplicates (default: 7)"
        ),
    ] = 7,
    amount_tolerance: Annotated[
        float,
        typer.Option(help="Dollar amount tolerance for fuzzy matching (default: 0.50)"),
    ] = 0.50,
    dry_run: Annotated[
        bool,
        typer.Option(help="Show what would be removed without making changes"),
    ] = False,
):
    """
    Deduplicate transactions in the master dataframe.

    This command finds and removes duplicate transactions including:
    - Exact duplicates
    - Pending -> Posted transactions (with amount changes)
    - Date-shifted transactions
    """
    if not Path(data_dir).exists():
        raise Exception(f"The data dir: '{data_dir}' does not exist!")

    print("Loading master transaction dataframe...")
    df = load_master_transaction_df(data_dir, validate=False, verbose=False)

    if df is None or df.empty:
        print("No transactions found in master file.")
        return

    original_count = len(df)
    print(f"Original transaction count: {original_count}")
    print("\nSearching for duplicates with:")
    print(f"  - Date window: {date_window} days")
    print(f"  - Amount tolerance: ${amount_tolerance}")

    # Run deduplication
    df_clean, stats = deduplicate_transactions(
        df,
        date_window=date_window,
        amount_tolerance=amount_tolerance,
        strategy="keep_latest",
        verbose=True,
    )

    if stats["removed_count"] == 0:
        print("\n✅ No duplicates found! Your data is clean.")
        return

    print(f"\n{'DRY RUN - ' if dry_run else ''}Results:")
    print(f"  - Duplicate groups found: {stats['duplicate_groups']}")
    print(f"  - Transactions in groups: {stats['transactions_in_groups']}")
    print(f"  - Duplicates to remove: {stats['removed_count']}")
    print(f"  - Final transaction count: {stats['final_count']}")

    if dry_run:
        print("\n🔍 This was a dry run. No changes were made.")
        print("   Run without --dry-run to apply the deduplication.")
    else:
        # Backup before making changes
        print("\nCreating backup of master file...")
        backup_master_transaction_df(data_dir, df)

        # Save the deduplicated dataframe
        print("Saving deduplicated master file...")
        save_master_transaction_df(
            data_path=data_dir, df=df_clean, verbose=False, validate=True
        )

        print(
            f"\n✅ Deduplication complete! Removed {stats['removed_count']} duplicate transactions."
        )
        print(f"   Backup created in: {Path(data_dir) / 'BACKUPS'}")


@config_app.command("update")
def config_update(data_dir: str = "."):
    config = load_config_file()
    update_config_file(config=config, path=data_dir)


@gsheets_app.command("sync")
def gsheets_sync(data_dir: str = "."):
    config = load_config_file(path=data_dir)
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
        config_path=data_dir,
    )
    response = gs_client.sync_all_sheets(df)
    print(response["message"])


if __name__ == "__main__":
    app()
