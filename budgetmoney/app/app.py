import streamlit as st
import pandas as pd
import sys
from pathlib import Path


# print(f"TESTING: {sys.argv[-1]}")

df_path = sys.argv[-1]
if not Path(df_path).exists():
    raise Exception(f"The transaction df path: '{df_path}' does not exist!")

st.title("My budgeting app")


df = pd.read_json(df_path, orient="records", lines=True)

edited_df = st.data_editor(df, use_container_width=True)
edited_df.to_json(df_path, orient="records", lines=True)
