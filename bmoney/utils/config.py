from pathlib import Path
import json
from bmoney.constants import (
    CONFIG_JSON_FILENAME,
    MASTER_DF_FILENAME,
    SHARED_EXPENSES,
    SHARED_NOTE_MSG,
    CAT_MAP,
    DATA_VIEW_COLS,
)


def create_config_file(path: str = "."):
    config_path = Path(path)
    config_path = Path(config_path / CONFIG_JSON_FILENAME)

    if config_path.exists():
        raise Exception("Config file already exists...")
    else:
        config_dict = {
            "MASTER_DF_FILENAME": MASTER_DF_FILENAME,
            "SHARED_EXPENSES": SHARED_EXPENSES,
            "SHARED_NOTE_MSG": SHARED_NOTE_MSG,
            "CAT_MAP": CAT_MAP,
            "DATA_VIEW_COLS": DATA_VIEW_COLS,
            "GSHEETS_CONFIG": {
                "SPREADSHEET_ID": "",
                "SPREADSHEET_TAB_NAME": "",
                "GCP_SERVICE_ACCOUNT_PATH": "",
            },
        }
        with open(config_path.resolve().as_posix(), "w") as file:
            json.dump(config_dict, file, indent=4)


def load_config_file(path: str = ".") -> dict:
    path = Path(path)
    if not Path(path / CONFIG_JSON_FILENAME).exists():
        print("Creating config file.")
        create_config_file(path)
    with open(Path(path / CONFIG_JSON_FILENAME).resolve().as_posix(), "r") as file:
        data = json.load(file)

    return data


def save_config_file(config: dict, path: str = "."):
    config_path = Path(Path(path) / CONFIG_JSON_FILENAME)
    with open(config_path.resolve().as_posix(), "w") as file:
        json.dump(config, file, indent=4)
