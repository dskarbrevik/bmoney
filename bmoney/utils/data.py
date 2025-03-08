from bmoney.constants import MASTER_DF_FILENAME

from pathlib import Path
from datetime import timedelta, datetime
from bmoney.constants import (
    CAT_MAP,
    SHARED_EXPENSES,
    SHARED_NOTE_MSG,
    NOT_SHARED_NOTE_MSG,
)
from bmoney.utils.config import load_config_file
import pandas as pd
import numpy as np
import os
import math
import uuid
from dotenv import load_dotenv

load_dotenv()


def has_csv_files(data_path: str) -> bool:
    """Checks for csv files in a dir

    Args:
        data_path (str): dir path to check

    Raises:
        Exception: if data_path doesn't exist

    Returns:
        bool: whether the data_dir contains csv files
    """

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


def backup_master_transaction_df(
    data_path: str, df: pd.DataFrame = None, verbose: bool = False
) -> None:
    master_backup_folder = Path(data_path).joinpath("BACKUPS")
    if not master_backup_folder.exists():
        print(f"{master_backup_folder.resolve()} does not exist. Creating...")
        master_backup_folder.resolve().mkdir()
    master_backup_path = Path(master_backup_folder).joinpath(
        f"backup-{int(datetime.timestamp(datetime.now()))}-{MASTER_DF_FILENAME}"
    )
    if verbose:
        print(f"Backing up master at: {master_backup_path}")
    df.to_json(master_backup_path, orient="records", lines=True)


def load_master_transaction_df(
    data_path: str, validate: bool = False, verbose: bool = True
) -> None:
    """Updates the master jsonl with any csvs in the data_path

    Args:
        data_path (str): where your rocket money transaction export csvs are located.
        validate (bool, optional): If true, tries to ensure the master df has the right columns etc. Defaults to False.
    """
    master_df_path = Path(data_path).joinpath(MASTER_DF_FILENAME)
    if master_df_path.exists():
        if verbose:
            print(f"Loading master transaction data from: {master_df_path}")
        df = pd.read_json(master_df_path, orient="records", lines=True)
        # df["Date"] = pd.to_datetime(df["Date"])
        if validate:
            backup_master_transaction_df(data_path, df)
            if verbose:
                print("Applying validation checks and transformations...")
            df = apply_transformations(df)
            if verbose:
                print(f"Saving validated dataframe to: '{master_df_path}'")
            df.to_json(master_df_path, orient="records", lines=True)
        return df
    else:
        print(f"No master file detected. Make sure it is named {MASTER_DF_FILENAME}")
        return None


def save_master_transaction_df(
    data_path: str, df: pd.DataFrame, verbose: bool = False, validate: bool = True
) -> None:
    """Saves a transaction dataframe to disk

    Args:
        data_path (str): where to save the df
        df (pd.DataFrame): dataframe to save
    """
    master_save_path = Path(data_path).joinpath(f"{MASTER_DF_FILENAME}")
    if validate:
        df = apply_transformations(df)
    if verbose:
        print(
            f"Saving new master transaction df to: {master_save_path.resolve().as_posix()}"
        )
    df.to_json(master_save_path.resolve().as_posix(), orient="records", lines=True)


def update_master_transaction_df(
    data_path: str = ".", return_df: bool = True, return_msg: bool = False
) -> pd.DataFrame:
    """Adds new transactions to master transaction df.
    Returns new df, saves to disk and creates backup of old df.

    Args:
        data_path (str): where your rocket money transaction export csvs are located.
        return_df (bool): whether you want the new df returned. Defaults to True.
        return_msg (bool): whether you want a str status message returned. Defaults to False.
    Returns:
        pd.DataFrame: new master df with new transactions
    """
    df = load_master_transaction_df(data_path, validate=False)
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame()

    # read through any transaction csvs in the data dir and add them to existing master transaction file
    files = [
        file
        for file in Path(data_path).iterdir()
        if file.is_file() and file.suffix == ".csv" and file.name != MASTER_DF_FILENAME
    ]
    if files:
        print("CSV transaction files found in data dir.")
        start_date = None
        old_master_rows = 0
        if not df.empty:
            start_date = df["Date"].max() + timedelta(days=1)
            old_master_rows = df.shape[0]
            print(
                f"Old master transaction data ends on {df['Date'].max().strftime('%m/%d/%Y')} and has num rows: {old_master_rows}"
            )
            backup_master_transaction_df(data_path, df)
        for file in files:
            tmp_df = pd.read_csv(file)
            tmp_df["Date"] = pd.to_datetime(tmp_df["Date"])
            if start_date:
                tmp_df = tmp_df[tmp_df["Date"] >= start_date]
            df = pd.concat([df, tmp_df])
    else:
        if return_msg:
            return "No csv files found to update master df with..."
        return None
    print(f"Added {df.shape[0] - old_master_rows} new transactions to master.")
    print("Applying validation checks and transformations...")
    df = apply_transformations(df)
    master_save_path = Path(data_path).joinpath(f"{MASTER_DF_FILENAME}")
    print(f"Saving new master transaction df to: {master_save_path}")
    df.to_json(master_save_path, orient="records", lines=True)
    print(df.shape)

    if return_df:
        return df
    if return_msg:
        return f"Transaction df updated, new df shape: {df.shape}"


def apply_transformations(df: pd.DataFrame) -> pd.DataFrame:
    """Adds columns to the trasnaction dataframe that help with downstream analytics.

    Args:
        df (pd.DataFrame): input dataframe

    Returns:
        pd.DataFrame: enriched dataframe
    """
    df = apply_latest(df)
    df = apply_custom_cat(df)
    df = apply_uuid(df)
    df = apply_month(df)
    df = apply_year(df)
    df = apply_amount_float(df)
    df = apply_shared(df)
    df = apply_note_check(df)

    return df


def apply_uuid(df: pd.DataFrame) -> pd.DataFrame:
    """Adds a column called UUID to the transaction dataframe

    Args:
        df (pd.DataFrame): input transaction dataframe

    Returns:
        pd.DataFrame: Same df you input with 1 new column "UUID"
    """
    if "BMONEY_TRANS_ID" not in df.columns:
        bmoney_ids = [str(uuid.uuid4()) for _ in range(df.shape[0])]
        df["BMONEY_TRANS_ID"] = bmoney_ids
    else:
        df["BMONEY_TRANS_ID"] = df["BMONEY_TRANS_ID"].apply(
            lambda x: x if pd.notna(x) else str(uuid.uuid4())
        )
    return df


def apply_note_check(df: pd.DataFrame) -> pd.DataFrame:
    """Auto updates SHARED col based on Note col values

    Args:
        df (pd.DataFrame): input transaction dataframe

    Returns:
        pd.DataFrame: Same df you input with SHARED col updated based on Note col
    """
    config = load_config_file()  # get user config

    df.loc[df["Note"].isnull(), "Note"] = ""
    df.loc[df["Note"].isin(["nan", "None"]), "Note"] = ""
    df["SHARED"] = df["SHARED"].astype(bool)
    df.loc[
        df["Note"]
        .str.lower()
        .str.strip()
        .str.contains(config.get("SHARED_NOTE_MSG", SHARED_NOTE_MSG)),
        "SHARED",
    ] = True

    df.loc[
        df["Note"]
        .str.lower()
        .str.strip()
        .str.contains(config.get("NOT_SHARED_NOTE_MSG", NOT_SHARED_NOTE_MSG)),
        "SHARED",
    ] = False

    return df


def apply_amount_float(df: pd.DataFrame) -> pd.DataFrame:
    """Adds a column called CUSTOM_CAT to the transaction dataframe

    Args:
        df (pd.DataFrame): input transaction dataframe

    Returns:
        pd.DataFrame: Same df you input with "Amount" col type cast to float and rounded to two decimal places.
    """

    df["Amount"] = df["Amount"].astype(float).round(2)

    return df


def apply_custom_cat(df: pd.DataFrame) -> pd.DataFrame:
    """Adds a column called CUSTOM_CAT to the transaction dataframe

    Args:
        df (pd.DataFrame): input transaction dataframe

    Returns:
        pd.DataFrame: Same df you input with 1 new column "CUSTOM_CAT"
    """
    config = load_config_file()  # get user config

    def custom_cat(row):
        if isinstance(row["LATEST_UPDATE"], float):
            edited_check = not math.isnan(row["LATEST_UPDATE"])
        elif isinstance(row["LATEST_UPDATE"], np.ndarray):
            edited_check = not np.isnan(row["LATEST_UPDATE"])
        elif not row["LATEST_UPDATE"]:
            edited_check = False
        if edited_check:
            if not row["CUSTOM_CAT"]:
                edited_check = False
        if not edited_check:
            #  if row["CUSTOM_CAT"]=="PET":
            #     print(f"NOT EDITED: Category for {row['Name']} is: {row['CUSTOM_CAT']} ({row['LATEST_UPDATE']})")
            return config.get("CAT_MAP", CAT_MAP).get(row["Category"], "UNKNOWN")
        else:
            # if row["CUSTOM_CAT"]=="PET":
            #     print(f"EDITED: Category for {row['Name']} is: {row['CUSTOM_CAT']} ({row['LATEST_UPDATE']})")
            return row["CUSTOM_CAT"]

    df["CUSTOM_CAT"] = df.apply(custom_cat, axis=1)

    return df


def apply_shared(df: pd.DataFrame) -> pd.DataFrame:
    """Adds a column called SHARED to the transaction dataframe

    Args:
        df (pd.DataFrame): input transaction dataframe

    Returns:
        pd.DataFrame: Same df you input with 1 new column "SHARED"
    """
    config = load_config_file()  # get user config

    if "SHARED" in df.columns:
        df["SHARED"] = np.where(
            df["SHARED"].isnull(),
            np.where(
                df["CUSTOM_CAT"].isin(config.get("SHARED_EXPENSES", SHARED_EXPENSES)),
                True,
                False,
            ),
            df["SHARED"],
        )

    else:
        df["SHARED"] = np.where(
            df["CUSTOM_CAT"].isin(config.get("SHARED_EXPENSES", SHARED_EXPENSES)),
            True,
            False,
        )
    return df


def apply_latest(df: pd.DataFrame) -> pd.DataFrame:
    """Adds a column called LATEST_UPDATE to the transaction dataframe representing the last time you update that row

    Args:
        df (pd.DataFrame): input transaction dataframe

    Returns:
        pd.DataFrame: Same df you input with 1 new column "LATEST_UPDATE"
    """
    if "LATEST_UPDATE" not in df.columns:
        df["LATEST_UPDATE"] = None
    return df


def apply_month(df: pd.DataFrame) -> pd.DataFrame:
    """Adds a column called MONTH to the transaction dataframe

    Args:
        df (pd.DataFramae): input transaction dataframe

    Returns:
        pd.DataFrame: Same df you input with 1 new column "MONTH"
    """

    df["MONTH"] = df["Date"].apply(lambda x: x.strftime("%m"))

    return df


def apply_year(df: pd.DataFrame) -> pd.DataFrame:
    """Adds a column called YEAR to the transaction dataframe

    Args:
        df (pd.DataFramae): input transaction dataframe

    Returns:
        pd.DataFrame: Same df you input with 1 new column "YEAR"
    """

    df["YEAR"] = df["Date"].apply(lambda x: x.strftime("%y"))

    return df


def monthly_gsheets_cost_table(
    df: pd.DataFrame,
    only_shared: bool = False,
    return_values: bool = False,
    start_date: str = None,
) -> pd.DataFrame:
    """Calculates total category spend per month

    Args:
        df (pd.DataFrame): transaction df
        only_shared (bool): If True, only return Categories in SHARED_EXPENSES. Defaults to False.
        return_values (bool): If True, returns data as list of lists instead of as dataframe. Defaults to False.

    Returns:
        pd.Series: total category spend per month
    """
    config = load_config_file()  # get user config
    if start_date:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df[df["Date"] >= start_date]
    if only_shared:
        df = df[df["SHARED"]]
    cat_df = (
        df.groupby(["MONTH", "YEAR", "CUSTOM_CAT", "SHARED"])["Amount"]
        .sum()
        .reset_index()
    )
    cat_df["Date"] = cat_df["MONTH"].astype(str) + "/" + cat_df["YEAR"].astype(str)
    cat_df["Person"] = config.get(
        "BUDGET_MONEY_USER", os.getenv("BUDGET_MONEY_USER", "UNKNOWN")
    )
    cat_df = cat_df.rename(columns={"CUSTOM_CAT": "Category"})
    if only_shared:
        cat_df = cat_df[
            cat_df["Category"].isin(config.get("SHARED_EXPENSES", SHARED_EXPENSES))
        ]
    cat_df = cat_df[["Date", "Person", "Category", "Amount"]]
    cat_df["dt"] = pd.to_datetime(cat_df["Date"], format="%m/%y")
    cat_df = cat_df.sort_values(by=["dt"], ascending=False, ignore_index=True)
    cat_df = cat_df.drop(columns="dt")
    cat_df["Amount"] = cat_df["Amount"].apply(np.round, args=(2,))
    pivot_df = pd.pivot_table(
        cat_df, index=["Date", "Person"], columns="Category", values="Amount"
    ).reset_index()
    # pivot_df = pivot_df.apply(round,axis=1)
    pivot_df = pivot_df.fillna(0)
    pivot_df.columns.name = None
    for cat in config.get("SHARED_EXPENSES", SHARED_EXPENSES):
        if cat not in pivot_df.columns:
            pivot_df[cat] = 0
    if return_values:
        pivot_df = [pivot_df.columns.tolist()] + pivot_df.values.tolist()
        pivot_df = clean_values(pivot_df)
    return pivot_df


def transactions_gsheet_table(
    df: pd.DataFrame,
    only_shared: bool = False,
    return_values: bool = False,
    start_date: str = None,
) -> pd.DataFrame:
    """Returns a table of transactions for gsheets

    Args:
        df (pd.DataFrame): transaction dataframe
        only_shared (bool): If True, only return Categories in SHARED_EXPENSES. Defaults to False.
        return_values (bool): If True, returns data as list of lists instead of as dataframe. Defaults to False.

    Returns:
        pd.DataFrame: table of transactions for gsheets
    """
    # config = load_config_file()  # get user config

    if only_shared:
        df = df[df["SHARED"]]
        # df = df[
        #     df["CUSTOM_CAT"].isin(config.get("SHARED_EXPENSES", SHARED_EXPENSES))
        # ]
    df = df[["Date", "Name", "Amount", "CUSTOM_CAT", "Note"]]
    df = df.rename(columns={"CUSTOM_CAT": "Category"})
    df["Date"] = pd.to_datetime(df["Date"])
    if start_date:
        df = df[df["Date"] >= start_date]
    df = df.sort_values(by=["Date"], ascending=False, ignore_index=True)
    df["Date"] = df["Date"].dt.strftime("%m/%d/%Y")
    if return_values:
        df = [df.columns.tolist()] + df.values.tolist()
        df = clean_values(df)
    return df


def last_30_cat_spend(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates spend across categories in last 30 days and delta from 30 days before that.

    Args:
        df (pd.DataFrame): transaction dataframe

    Returns:
        pd.DataFrame: calculated metrics
    """
    end_date = datetime.now()
    start_date = datetime.now() - timedelta(days=30)
    current_df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]
    end_date = start_date - timedelta(days=1)
    start_date = end_date - timedelta(days=30)
    past_df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

    current_cat_spending = (
        current_df.groupby("CUSTOM_CAT")["Amount"].sum().reset_index()
    )
    current_cat_spending = current_cat_spending.rename(
        columns={"Amount": "Current Amount"}
    )
    past_cat_spending = past_df.groupby("CUSTOM_CAT")["Amount"].sum().reset_index()
    past_cat_spending = past_cat_spending.rename(columns={"Amount": "Past Amount"})
    combine_df = current_cat_spending.merge(past_cat_spending, how="outer")
    combine_df = combine_df.fillna(0)
    combine_df["Delta"] = combine_df["Current Amount"] - combine_df["Past Amount"]
    combine_df["pct_delta"] = (
        (combine_df["Current Amount"] / combine_df["Past Amount"]) - 1
    ) * 100
    # combine_df["pct_delta"] = combine_df["pct_delta"].apply(lambda x: f"{np.round(x)}%" if (isinstance(x, float) or isinstance(x, np.inf)) else x)
    # combine_df["pct_delta"] = combine_df["pct_delta"].replace(np.inf, "inf%")
    return combine_df, datetime.now() - timedelta(days=30), datetime.now()


def get_category_cost(
    df: pd.DataFrame,
    cat: str,
    cat_col: str = "CUSTOM_CAT",
    start_date: datetime = None,
    end_date: datetime = None,
    stat_type: str = "total",
) -> float:
    """Calculates useful statistics. For example, total spending on food last month.

    Args:
        df (pd.DataFrame): transactions dataframe to use.
        cat (str): value of category of interest.
        cat_col (str, optional): name of df col of interest. Defaults to "CUSTOM_CAT".
        start_date (datetime.datetime, optional): start datetime for calculation. Defaults to no minimum.
        end_date (datetime.datetime, optional): end datetime for calculation. Defaults to maximum.
        stat_type (str, optional): metric to return. Choices are "total","average","median". Defaults to "total".

    Returns:
        float: calculated metric
    """

    df["Date"] = pd.to_datetime(df["Date"])

    if start_date and isinstance(start_date, datetime):
        df = df[df["Date"] >= start_date]
    if end_date and isinstance(end_date, datetime):
        df = df[df["Date"] <= end_date]

    df = df[df[cat_col] == cat]

    if stat_type == "total":
        return df["Amount"].sum()
    elif stat_type == "average":
        return df["Amount"].mean()
    elif stat_type == "median":
        return df["Amount"].median()
    else:
        raise Exception(
            f"stat_type must be either 'total', 'average', or 'median'. Not '{stat_type}'."
        )


def clean_values(values):
    for i, row in enumerate(values):
        for j, val in enumerate(row):
            if isinstance(val, str):
                val = val.replace("'", "")
                values[i][j] = val

    return values
