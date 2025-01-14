import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from budgetmoney.utils.data import last_30_cat_spend, load_master_transaction_df
from budgetmoney.utils.gcloud import GSheetsClient
from budgetmoney.constants import (
    MASTER_DF_FILENAME,
    SHARED_EXPENSES,
    CAT_MAP,
    DATA_VIEW_COLS,
)
from datetime import datetime, timedelta
import calendar

from dotenv import load_dotenv
import os

load_dotenv()

# print(f"TESTING: {sys.argv[-1]}")
# Establish existance of master transaction jsonl rocket money data

if "data_path" not in st.session_state:
    data_path = sys.argv[-1]
    df_path = Path(data_path).joinpath(MASTER_DF_FILENAME).resolve().as_posix()
    if not Path(df_path).exists():
        if Path(data_path).exists():
            df = load_master_transaction_df(data_path)
            if not isinstance(df, pd.DataFrame):
                raise FileNotFoundError(
                    f"There is no master transaction jsonl in your data dir ('{MASTER_DF_FILENAME}').\n\nMake sure there is a rocket money transaciton csv in the data dir and try `bmoney update {data_path}` before launching the bmoney app again."
                )
        else:
            raise FileNotFoundError(f"The data path: '{data_path}' does not exist!")
    st.session_state.data_path = data_path
    st.session_state.df_path = df_path

if "df" not in st.session_state:
    df = pd.read_json(df_path, orient="records", lines=True)
    df["Date"] = pd.to_datetime(df["Date"])
    st.session_state.df = df
if "edit_df" not in st.session_state:
    st.session_state.edit_df = df.copy()

now = datetime.now()
this_month_str = now.strftime("%m/%Y")
start_of_month = datetime(now.year, now.month, 1)
last_day_of_month = calendar.monthrange(now.year, now.month)[1]
end_of_month = datetime(now.year, now.month, last_day_of_month, 23, 59, 59)

gclient = GSheetsClient(
    sheet_id=os.getenv("SPREADSHEET_ID"),
    sa_cred_path=os.getenv("GCP_SERVICE_ACCOUNT_PATH"),
)

st.set_page_config(page_title="Budget Money", page_icon="\U0001f680", layout="wide")
st.title("Budget Money 🚀")
st.divider()
username = os.getenv("BUDGET_MONEY_USER")
st.header(f"Hi {username}! Happy {datetime.now().strftime('%A')} 😎")
tab1, tab2 = st.tabs(["📈 Mission Control", "🗃 Data Editor"])

with tab1:
    num_cols = len(SHARED_EXPENSES)
    st.subheader(
        f"Last 30 days Dashboard ({datetime.now().strftime('%d/%m')} - {(datetime.now() - timedelta(days=30)).strftime('%d/%m')})"
    )
    columns = st.columns(num_cols)
    last_30_df, start, end = last_30_cat_spend(st.session_state.df)

    col = 0
    for i, row in last_30_df.iterrows():
        if row["CUSTOM_CAT"] in SHARED_EXPENSES:
            with columns[col]:
                st.metric(
                    label=row["CUSTOM_CAT"],
                    value=round(row["Current Amount"], 2),
                    delta=f"{np.round(row["pct_delta"])}%",
                    delta_color="inverse",
                    border=True,
                )
            col += 1

with tab2:
    st.header("Data Editor")

    if st.button("Sync data to gsheets"):
        response = gclient.sync_sheet(
            st.session_state.edit_df, sheet_name=os.getenv("SPREADSHEET_TAB_NAME")
        )
        if response["status"] == 1:
            st.toast(f"Sync successful!\n\n{response["message"]}", icon="👌")
        else:
            st.toast(f"Sync failed!\n\n{response["message"]}", icon="❌")

    # if st.button("Merge transaction datasets"):
    #     response = update_master_transaction_df(
    #         data_path, return_df=False, return_msg=True
    #     )

    today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    two_months_ago = datetime.combine(
        (datetime.now() - pd.DateOffset(months=2)), datetime.min.time()
    )

    #######
    if "show_more_text" not in st.session_state:
        st.session_state.show_more_text = "show more"

    def change_text():
        if st.session_state.show_more_text == "show less":
            st.session_state.show_more_text = "show more"
        else:
            st.session_state.show_more_text = "show less"

    def save_df():
        if not st.session_state.df.equals(st.session_state.edit_df):
            st.session_state.edit_df.to_json(
                st.session_state.df_path, orient="records", lines=True
            )
            st.toast("Save successful!", icon="👌")
            st.session_state.df = load_master_transaction_df(st.session_state.data_path)
        else:
            st.toast("Data has not changed yet...", icon="❌")

    st.button(st.session_state.show_more_text, on_click=change_text)

    st.button("Save changes", on_click=save_df)

    # mybutton = st.button("show more")

    # if st.button(st.session_state.show_more_text):

    # if "show_more_text" not in st.session_state:
    #     st.session_state.show_more_text = "show all rows"
    # if "button_clicked" not in st.session_state:
    #     st.session_state.button_clicked = False

    # # Button with dynamic label
    # if st.button(st.session_state.show_more_text):
    #     st.session_state.button_clicked = True

    # # Update the label based on button click
    # if st.session_state.button_clicked:
    #     if st.session_state.show_more_text == "show all rows":
    #         st.session_state.show_more_text = "show less"
    #     else:
    #         st.session_state.show_more_text = "show all rows"
    #     st.session_state.button_clicked = False  # Reset clicked status

    # Display the current button label
    # st.write("Current button label:", st.session_state.show_more_text)

    if st.session_state.show_more_text == "show less":  # show full dataframe
        edit_df = st.data_editor(
            st.session_state.edit_df[DATA_VIEW_COLS],
            column_config={
                "CUSTOM_CAT": st.column_config.SelectboxColumn(
                    "CUSTOM_CAT", options=list(set(CAT_MAP.values())), required=True
                ),
                "SHARED": st.column_config.CheckboxColumn("SHARED", pinned=True),
                "Date": None,
            },
        )
        st.session_state.edit_df = edit_df
    else:  # show slice of dataframe
        edit_df = st.data_editor(
            st.session_state.edit_df[
                st.session_state.edit_df["Date"] >= two_months_ago
            ][DATA_VIEW_COLS],
            column_config={
                "CUSTOM_CAT": st.column_config.SelectboxColumn(
                    "CUSTOM_CAT", options=list(set(CAT_MAP.values())), required=True
                ),
                "SHARED": st.column_config.CheckboxColumn("SHARED", pinned=True),
                "Date": None,
            },
        )
        st.session_state.edit_df.loc[edit_df.index, edit_df.columns] = edit_df
