import typer
from budgetmoney.utils import has_csv_files, update_master_transaction_df

# from streamlit.web import cli as stcli
from pathlib import Path
from importlib.util import find_spec
import subprocess
# import logging
# logging.getLogger('streamlit.runtime.scriptrunner.script_runner').setLevel(logging.ERROR)


def start_app(data_dir: str):
    # if not master_jsonl_name:
    #     master_jsonl_name = MASTER_DF_FILENAME
    if has_csv_files(data_dir):
        update_master_transaction_df(data_dir)

    master_jsonl_name = "BUDGET_MONEY_TRANSACTIONS.jsonl"
    df_path = Path(data_dir).resolve()
    df_path = df_path.joinpath(master_jsonl_name)

    # stcli.main_run(find_spec("budgetmoney.app.app").origin)

    app_location = find_spec("budgetmoney.app.app").origin
    subprocess.run(["streamlit", "run", app_location, "--", f"{df_path}"])


def main():
    typer.run(start_app)


if __name__ == "__main__":
    main()
