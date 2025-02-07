import streamlit as st
import pandas as pd
import numpy as np
import sys
from bmoney.utils.data import (
    last_30_cat_spend,
    load_master_transaction_df,
    save_master_transaction_df,
    backup_master_transaction_df,
)
from bmoney.utils.gcloud import GSheetsClient
from bmoney.constants import (
    SHARED_EXPENSES,
    CAT_MAP,
    DATA_VIEW_COLS,
)
from bmoney.utils.config import load_config_file, run_custom_script

from datetime import datetime, timedelta
import calendar

from dotenv import load_dotenv
import os

load_dotenv()  # get env vars

data_dir = sys.argv[-1]
config = load_config_file(data_dir)  # get user config

st.set_page_config(
    page_title="Budget Money",
    page_icon="\U0001f680",
    layout="wide",
    menu_items={
        "About": None,
        "Report a bug": "https://github.com/dskarbrevik/bmoney/issues",
    },
)


@st.cache_data
def cached_run_custom_script(script_path, function_name, *args, **kwargs):
    """Caches the result of the expensive function."""
    return run_custom_script(script_path, function_name, *args, **kwargs)


def change_text():
    if st.session_state.show_more_text == "show less":
        st.session_state.session_df = st.session_state.edit_df.copy()
        st.session_state.show_more_text = "show more"
    else:
        st.session_state.session_df = st.session_state.edit_df.copy()
        st.session_state.show_more_text = "show less"


def save_df():
    if not st.session_state.df.equals(st.session_state.edit_df):
        backup_master_transaction_df(
            data_path=st.session_state.data_path, df=st.session_state.df
        )
        st.session_state.df = st.session_state.edit_df.copy()
        # print(st.session_state.edit_df.iloc[1347])
        # st.session_state.edit_df = apply_transformations(st.session_state.edit_df)
        # print(st.session_state.edit_df.iloc[1347])
        save_master_transaction_df(
            data_path=st.session_state.data_path,
            df=st.session_state.edit_df,
            verbose=True,
        )
        st.toast("Save successful!", icon="👌")
        # print(st.session_state.edit_df.iloc[224])
        # st.session_state.edit_df = st.session_state.df.copy()
        # print(st.session_state.edit_df.iloc[224])
        # st.session_state.session_df = st.session_state.df.copy()
    else:
        st.toast("Data has not changed yet...", icon="❌")


def update_all_df():
    if st.session_state["edit_all_df"]["edited_rows"]:
        tmp_df = pd.DataFrame.from_dict(
            st.session_state["edit_all_df"]["edited_rows"], orient="index"
        )
        st.session_state.edit_df.loc[tmp_df.index, tmp_df.columns] = tmp_df.copy()
        update_time = int(round(datetime.now().timestamp()))
        st.session_state.edit_df.loc[
            st.session_state["edit_all_df"]["edited_rows"].keys(), "LATEST_UPDATE"
        ] = update_time


# IMPORTANT TIME CONSTRUCTS AND SETUP
num_rows_display = 20
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
    st.session_state.data_path = data_dir

if "df" not in st.session_state:
    df = load_master_transaction_df(st.session_state.data_path, verbose=False)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Note"] = df["Note"].astype(str)
    df["SHARED"] = df["SHARED"].astype(bool)

    df = df.reset_index(drop=True)
    st.session_state.df = df
if "edit_df" not in st.session_state:
    st.session_state.edit_df = st.session_state.df.copy()
if "session_df" not in st.session_state:
    st.session_state.session_df = st.session_state.df.copy()
# if "edit_all_df" not in st.session_state:
#     st.session_state.edit_all_df = st.session_state.edit_df.copy()
# if "edit_slice_df" not in st.session_state:
#     st.session_state.edit_slice_df = st.session_state.edit_df[
#         st.session_state.edit_df["Date"] >= two_months_ago
#     ].copy()

# google spreadsheets client init
try:
    gclient = GSheetsClient(
        sheet_id=config.get("GSHEETS_CONFIG").get("SPREADSHEET_ID")
        or os.getenv("SPREADSHEET_ID"),
        sa_cred_path=config.get("GSHEETS_CONFIG").get("GCP_SERVICE_ACCOUNT_PATH")
        or os.getenv("GCP_SERVICE_ACCOUNT_PATH"),
    )
except Exception:
    gclient = None
    # st.warning("Google Sheets client failed to initialize.")

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
        f"Last 30 days Dashboard ({(datetime.now() - timedelta(days=30)).strftime('%m/%d')} - {datetime.now().strftime('%m/%d')})"
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

    if config.get("CUSTOM_WIDGETS"):
        custom_num_cols = len(config.get("CUSTOM_WIDGETS"))
        custom_num_cols = max(custom_num_cols, 5)
        st.subheader("Custom Widgets")
        custom_columns = st.columns(custom_num_cols)
        cols = 0
        for widget in config.get("CUSTOM_WIDGETS"):
            with custom_columns[cols]:
                widget_data = cached_run_custom_script(
                    script_path=widget.get("script_path"),
                    function_name=widget.get("function_name"),
                    *widget.get("args"),
                    **widget.get("kwargs"),
                )
                if widget.get("type") == "metric":
                    if widget_data.get("delta"):
                        st.metric(
                            label=widget_data.get("title"),
                            value=widget_data.get("value"),
                            delta=f"{widget_data.get('delta')}%",
                            border=True,
                        )
                    else:
                        st.metric(
                            label=widget_data.get("title"),
                            value=widget_data.get("value"),
                            border=True,
                        )
            cols += 1

# data editor view
with tab2:
    st.header("Data Editor")
    col1, col2, col3 = st.columns([0.15, 0.15, 0.7])
    with col1:
        st.button("Save changes to local master file", on_click=save_df)
    with col2:
        if st.button("Sync data to gsheets"):
            if not gclient:
                st.warning("Google Sheets client failed to initialize.")
            else:
                if not st.session_state.df.equals(st.session_state.edit_df):
                    st.toast(
                        "WARNING: You have unsaved changes in the data editor that were included in the gsheets sync. Consider saving changes."
                    )
                response = gclient.sync_all_sheets(st.session_state.edit_df)
                if response["status"] == 1:
                    st.toast("Sync successful!", icon="👌")
                else:
                    st.toast(f"Sync failed!\n\n{response['message']}", icon="❌")

    st.divider()

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
        height=(num_rows_display + 1) * 35 + 3,
        key="edit_all_df",
        on_change=update_all_df,
    )
