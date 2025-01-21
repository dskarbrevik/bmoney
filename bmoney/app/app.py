import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from bmoney.utils.data import (
    last_30_cat_spend,
    load_master_transaction_df,
    apply_transformations,
)
from bmoney.utils.gcloud import GSheetsClient
from bmoney.constants import (
    MASTER_DF_FILENAME,
    SHARED_EXPENSES,
    CAT_MAP,
    DATA_VIEW_COLS,
)
from bmoney.utils.config import load_config_file

from datetime import datetime, timedelta
import calendar

from dotenv import load_dotenv
import os

load_dotenv()  # get env vars
config = load_config_file()  # get user config


def change_text():
    if st.session_state.show_more_text == "show less":
        st.session_state.session_df = st.session_state.edit_df.copy()
        st.session_state.show_more_text = "show more"
    else:
        st.session_state.session_df = st.session_state.edit_df.copy()
        st.session_state.show_more_text = "show less"


def save_df():
    if not st.session_state.df.equals(st.session_state.edit_df):
        st.session_state.edit_df.to_json(
            st.session_state.df_backup_path, orient="records", lines=True
        )
        st.session_state.edit_df = apply_transformations(st.session_state.edit_df)
        st.session_state.edit_df.to_json(
            st.session_state.df_path, orient="records", lines=True
        )
        st.toast("Save successful!", icon="👌")
        st.session_state.df = load_master_transaction_df(
            st.session_state.data_path, validate=False
        )
        st.session_state.edit_df = st.session_state.df.copy()
        st.session_state.session_df = st.session_state.df.copy()
    else:
        st.toast("Data has not changed yet...", icon="❌")


def update_all_df():
    if st.session_state["edit_all_df"]["edited_rows"]:
        st.session_state.tmp_df = pd.DataFrame.from_dict(
            st.session_state["edit_all_df"]["edited_rows"], orient="index"
        )
        st.session_state.edit_df.loc[
            st.session_state.tmp_df.index, st.session_state.tmp_df.columns
        ] = st.session_state.tmp_df.copy()
        update_time = int(round(datetime.now().timestamp()))
        st.session_state.edit_df.loc[
            st.session_state["edit_all_df"]["edited_rows"].keys(), "LATEST_UPDATE"
        ] = update_time
        # st.session_state.edit_df["LATEST_UPDATE"] = st.session_state.edit_df["LATEST_UPDATE"].astype(int)


def update_slice_df():
    if st.session_state["edit_slice_df"]["edited_rows"]:
        st.session_state.tmp_df = pd.DataFrame.from_dict(
            st.session_state["edit_slice_df"]["edited_rows"], orient="index"
        )
        st.session_state.edit_df.loc[
            st.session_state.tmp_df.index, st.session_state.tmp_df.columns
        ] = st.session_state.tmp_df.copy()
        update_time = int(round(datetime.now().timestamp()))
        st.session_state.edit_df.loc[
            st.session_state["edit_slice_df"]["edited_rows"].keys(), "LATEST_UPDATE"
        ] = update_time
        # st.session_state.edit_df["LATEST_UPDATE"] = st.session_state.edit_df["LATEST_UPDATE"].astype(int)


# IMPORTANT TIME CONSTRUCTS
now = datetime.now()
this_month_str = now.strftime("%m/%Y")
start_of_month = datetime(now.year, now.month, 1)
last_day_of_month = calendar.monthrange(now.year, now.month)[1]
end_of_month = datetime(now.year, now.month, last_day_of_month, 23, 59, 59)
today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
two_months_ago = datetime.combine(
    (datetime.now() - pd.DateOffset(months=2)), datetime.min.time()
)

# INITIALIZE SESSION STATE VARIABLES
if "data_path" not in st.session_state:
    data_path = sys.argv[-1]
    df_path = (
        Path(data_path)
        .joinpath(config.get("MASTER_DF_FILENAME", MASTER_DF_FILENAME))
        .resolve()
        .as_posix()
    )
    if not Path(df_path).exists():
        if Path(data_path).exists():
            df = load_master_transaction_df(data_path)
            if not isinstance(df, pd.DataFrame):
                raise FileNotFoundError(
                    f"There is no master transaction jsonl in your data dir ('{config.get('MASTER_DF_FILENAME', MASTER_DF_FILENAME)}').\n\nMake sure there is a rocket money transaciton csv in the data dir and try `bmoney update {data_path}` before launching the bmoney app again."
                )
        else:
            raise FileNotFoundError(f"The data path: '{data_path}' does not exist!")
    st.session_state.data_path = data_path
    st.session_state.df_path = df_path
    st.session_state.df_backup_path = Path(data_path).joinpath(
        f"backup_{config.get('MASTER_DF_FILENAME', MASTER_DF_FILENAME)}"
    )
if "df" not in st.session_state:
    df = pd.read_json(df_path, orient="records", lines=True)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Note"] = df["Note"].astype(str)
    st.session_state.df = df
if "edit_df" not in st.session_state:
    st.session_state.edit_df = df.copy()
if "session_df" not in st.session_state:
    st.session_state.session_df = df.copy()
# if "edit_all_df" not in st.session_state:
#     st.session_state.edit_all_df = st.session_state.edit_df.copy()
# if "edit_slice_df" not in st.session_state:
#     st.session_state.edit_slice_df = st.session_state.edit_df[
#         st.session_state.edit_df["Date"] >= two_months_ago
#     ].copy()

# google spreadsheets client init
gclient = GSheetsClient(
    sheet_id=config.get("GSHEETS_CONFIG").get("SPREADSHEET_ID")
    or os.getenv("SPREADSHEET_ID"),
    sa_cred_path=config.get("GSHEETS_CONFIG").get("GCP_SERVICE_ACCOUNT_PATH")
    or os.getenv("GCP_SERVICE_ACCOUNT_PATH"),
)


st.set_page_config(
    page_title="Budget Money",
    page_icon="\U0001f680",
    layout="wide",
    menu_items={
        "About": None,
        "Report a bug": "https://github.com/dskarbrevik/bmoney/issues",
    },
)
# st.config.set_option('client.toolbarMode', 'viewer')
# Main app setup
st.markdown(
    """
    <style>
    .stAppDeployButton {
        visibility: hidden;
    }
    </style>
""",
    unsafe_allow_html=True,
)
st.title("Budget Money 🚀")
username = config.get("BUDGET_MONEY_USER", os.getenv("BUDGET_MONEY_USER"))
st.subheader(f"Hi {username}! Happy {datetime.now().strftime('%A')} 😎")
tab1, tab2 = st.tabs(["📈 Mission Control", "🗃 Data Editor"])

# dashboard view
with tab1:
    num_cols = len(config.get("SHARED_EXPENSES", SHARED_EXPENSES))
    st.subheader(
        f"Last 30 days Dashboard ({datetime.now().strftime('%m/%d')} - {(datetime.now() - timedelta(days=30)).strftime('%m/%d')})"
    )
    columns = st.columns(num_cols)
    last_30_df, start, end = last_30_cat_spend(st.session_state.df)

    col = 0
    for i, row in last_30_df.iterrows():
        if row["CUSTOM_CAT"] in config.get("SHARED_EXPENSES", SHARED_EXPENSES):
            with columns[col]:
                st.metric(
                    label=row["CUSTOM_CAT"],
                    value=round(row["Current Amount"], 2),
                    delta=f"{np.round(row['pct_delta'])}%",
                    delta_color="inverse",
                    border=True,
                )
            col += 1

# data editor view
with tab2:
    st.header("Data Editor")
    if st.button("Sync data to gsheets"):
        gsheet_df = load_master_transaction_df(
            st.session_state.data_path, validate=False
        )
        if not gsheet_df.equals(st.session_state.session_df):
            st.toast(
                "WARNING: You have unsaved changes in the data editor that were included in the gsheets sync. Please consider saving changes."
            )
        response = gclient.sync_sheet(
            gsheet_df,
            sheet_name=config.get("GSHEETS_CONFIG").get("SPREADSHEET_TAB_NAME")
            or os.getenv("SPREADSHEET_TAB_NAME"),
        )
        if response["status"] == 1:
            st.toast("Sync successful!", icon="👌")
        else:
            st.toast(f"Sync failed!\n\n{response['message']}", icon="❌")
    st.divider()

    col1, col2, col3 = st.columns([0.15, 0.15, 0.7])
    with col1:
        if "show_more_text" not in st.session_state:
            st.session_state.show_more_text = "show more"
        st.button(st.session_state.show_more_text, on_click=change_text)
    with col2:
        st.button("Save changes to local master file", on_click=save_df)

    if st.session_state.show_more_text == "show less":  # show full dataframe
        st.data_editor(
            st.session_state.session_df[config.get("DATA_VIEW_COLS", DATA_VIEW_COLS)],
            column_config={
                "SHARED": st.column_config.CheckboxColumn("SHARED", pinned=True),
                "CUSTOM_CAT": st.column_config.SelectboxColumn(
                    "CUSTOM_CAT",
                    options=list(
                        set(config.get("CAT_MAP", CAT_MAP).values()).union(
                            set(config.get("SHARED_EXPENSES", SHARED_EXPENSES))
                        )
                    ),
                    required=True,
                    pinned=True,
                ),
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    options=list(set(config.get("CAT_MAP", CAT_MAP).keys())),
                    required=True,
                ),
                "Note": st.column_config.TextColumn("Note"),
                "Date": None,
            },
            hide_index=True,
            key="edit_all_df",
            on_change=update_all_df,
        )
    else:  # show slice of dataframe
        st.data_editor(
            st.session_state.session_df[
                st.session_state.session_df["Date"] >= two_months_ago
            ][config.get("DATA_VIEW_COLS", DATA_VIEW_COLS)],
            column_config={
                "SHARED": st.column_config.CheckboxColumn("SHARED", pinned=True),
                "CUSTOM_CAT": st.column_config.SelectboxColumn(
                    "CUSTOM_CAT",
                    options=list(
                        set(config.get("CAT_MAP", CAT_MAP).values()).union(
                            set(config.get("SHARED_EXPENSES", SHARED_EXPENSES))
                        )
                    ),
                    required=True,
                    pinned=True,
                ),
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    options=list(set(config.get("CAT_MAP", CAT_MAP).keys())),
                    required=True,
                ),
                "Note": st.column_config.TextColumn("Note"),
                "Date": None,
            },
            hide_index=True,
            key="edit_slice_df",
            on_change=update_slice_df,
        )
