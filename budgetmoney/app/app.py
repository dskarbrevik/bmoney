import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from budgetmoney.utils.data import last_30_cat_spend, update_master_transaction_df
from budgetmoney.utils.gcloud import GSheetsClient
from budgetmoney.constants import (MASTER_DF_FILENAME, 
                                   SHARED_EXPENSES, 
                                   CAT_MAP, 
                                   DATA_VIEW_COLS)
from datetime import datetime, timedelta
import calendar

from dotenv import load_dotenv
import os

load_dotenv()

# print(f"TESTING: {sys.argv[-1]}")

data_path = sys.argv[-1]
df_path = Path(data_path).joinpath(MASTER_DF_FILENAME).resolve().as_posix()
if not Path(df_path).exists():
    if Path(data_path).exists():
        df = update_master_transaction_df(data_path)
        if not isinstance(df, pd.DataFrame):
            raise FileNotFoundError("There may not be a master jsonl or rocket money csv export file in your data dir.")
    else:
        raise FileNotFoundError(f"The data path: '{data_path}' does not exist!")


df = pd.read_json(df_path, orient="records", lines=True)


df["Date"] = pd.to_datetime(df["Date"])
now = datetime.now()
this_month_str = now.strftime("%m/%Y")
start_of_month = datetime(now.year, now.month, 1)
last_day_of_month = calendar.monthrange(now.year, now.month)[1]
end_of_month = datetime(now.year, now.month, last_day_of_month, 23, 59, 59)

gclient = GSheetsClient(
    sheet_id=os.getenv("SPREADSHEET_ID"),
    sa_cred_path=os.getenv("GCP_SERVICE_ACCOUNT_PATH"),
)

st.set_page_config(
    page_title="Budget Money", page_icon="\U0001f680", layout="wide"
)
st.title("Budget Money 🚀")
st.divider()
username = os.getenv("BUDGET_MONEY_USER")
st.header(f"Hi {username}! Happy {datetime.now().strftime('%A')} 😎")
tab1, tab2 = st.tabs(["📈 Mission Control", "🗃 Data Editor"])

with tab1:
    num_cols = len(SHARED_EXPENSES)
    st.subheader(f"Last 30 days Dashboard ({datetime.now().strftime('%d/%m')} - {(datetime.now() - timedelta(days=30)).strftime('%d/%m')})")
    columns = st.columns(num_cols)
    last_30_df, start, end = last_30_cat_spend(df)

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
        response = gclient.sync_sheet(df,
                                  sheet_name=os.getenv('SPREADSHEET_TAB_NAME'))
        if response["status"]==1:
            st.toast(f"Sync successful!\n\n{response["message"]}", icon="👌")
        else:
            st.toast(f"Sync failed!\n\n{response["message"]}", icon="❌")

    if st.button("Merge transaction datasets"):
        response = update_master_transaction_df(data_path,
                                                return_df=False,
                                                return_msg=True)


    today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    two_months_ago = datetime.combine(
        (datetime.now() - pd.DateOffset(months=2)), datetime.min.time()
    )

    # Initialize session state for toggle
    if "show_all" not in st.session_state:
        st.session_state.show_all = False

    # Toggle the state when the button is pressed
    if st.button("Show More / Show Less"):
        st.session_state.show_all = not st.session_state.show_all

    # Display DataFrame based on state
    if st.session_state.show_all:
        st.data_editor(df[DATA_VIEW_COLS],
                       column_config={
                           "CUSTOM_CAT": st.column_config.SelectboxColumn(
                               "CUSTOM_CAT",
                               options=list(set(CAT_MAP.values())),
                               required=True
                           ),
                            "SHARED": st.column_config.SelectboxColumn(
                                "SHARED",
                                options=[True,False],
                                required=True
                            )
                       })  # Show all rows
    else:
        st.data_editor(
            df[df["Date"] >= two_months_ago][DATA_VIEW_COLS],
            column_config={
                           "CUSTOM_CAT": st.column_config.SelectboxColumn(
                               "CUSTOM_CAT",
                               options=list(set(CAT_MAP.values())),
                               required=True
                           ),
                            "SHARED": st.column_config.SelectboxColumn(
                                "SHARED",
                                options=[True,False],
                                required=True
                            )
                       }
        )  # Show a slice of the DataFrame
