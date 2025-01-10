from budgetmoney.constants import MASTER_DF_FILENAME

from pathlib import Path
from datetime import timedelta

import pandas as pd


def has_csv_files(data_path: str) -> bool:
    """Checks for csv files in a dir"""

    dir = Path(data_path)
    if dir.is_dir():
        return any(
            [
                True if file.is_file() and file.suffix == ".csv" else False
                for file in Path(data_path).iterdir()
            ]
        )
    else:
        raise Exception(f"Path '{data_path}' is not a directory.")


def update_master_transaction_df(
    data_path: str, master_jsonl_filename: str = None
) -> None:
    """_summary_

    Args:
        data_path (str): _description_
        master_jsonl_filename (str, optional): _description_. Defaults to None.
    """

    # initialize the master transaction file
    data_path = Path(data_path)
    if not master_jsonl_filename:
        master_jsonl_filename = MASTER_DF_FILENAME
    master_df_path = Path(data_path / master_jsonl_filename)
    master_backup_path = Path(data_path / f"backup_{master_jsonl_filename}")
    if master_df_path.exists():
        print(f"Loading master transaction data from: {master_df_path}")
        df = pd.read_json(master_df_path, lines=True)
        df["Date"] = pd.to_datetime(df["Date"])
        start_date = df["Date"].max() + timedelta(days=1)
        print(
            f"Master transaction data ends on {df["Date"].max()} and has shape: {df.shape}"
        )
        print(f"Backup of master being made at: {master_backup_path}")
        df.to_json(master_backup_path, orient="records", lines=True)
    else:
        print("No master file detected. Creating new master file.")
        df = pd.DataFrame()
        start_date = None

    # read through any transaction csvs in the data dir and add them to existing master transaction file
    files = [
        file
        for file in data_path.iterdir()
        if file.is_file()
        and file.suffix == ".csv"
        and file.name != master_jsonl_filename
    ]
    for file in files:
        print(file)
        tmp_df = pd.read_csv(file)
        tmp_df["Date"] = pd.to_datetime(tmp_df["Date"])
        tmp_df = tmp_df[tmp_df["Date"] >= start_date]
        df = pd.concat([df, tmp_df])
    print(f"New master transaction df shape: {df.shape}")
    print(f"Saving new master transaction df to: {master_df_path}")
    df.to_json(master_df_path, orient="records", lines=True)
    print(df.shape)
