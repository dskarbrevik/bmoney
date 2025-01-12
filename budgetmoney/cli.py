import typer
from pathlib import Path
from importlib.util import find_spec
import subprocess


def start_app(data_dir: str):
    if not Path(data_dir).exists():
        raise Exception(f"The data dir: '{data_dir}' does not exist!")
    app_location = find_spec("budgetmoney.app.app").origin
    subprocess.run(["streamlit", "run", app_location, "--", f"{data_dir}"])


def main():
    typer.run(start_app)


if __name__ == "__main__":
    main()
