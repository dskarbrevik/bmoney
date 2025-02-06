from pathlib import Path
import json
from bmoney.constants import (
    CONFIG_JSON_FILENAME,
    DEFAULT_CONFIG,
)
import importlib.util
import sys

"""
Controls the config.json file that is used to store user settings.
"""


def create_config_file(path: str = ".", force: bool = False):
    config_path = Path(path)
    config_path = Path(config_path / CONFIG_JSON_FILENAME)

    if config_path.exists() and not force:
        raise Exception("Config file already exists...")
    else:
        if force:
            print("config file exists but overwriting with force...")
        config_dict = DEFAULT_CONFIG
        with open(config_path.resolve().as_posix(), "w") as file:
            json.dump(config_dict, file, indent=4)


def load_config_file(path: str = ".") -> dict:
    path = Path(path)
    if not Path(path / CONFIG_JSON_FILENAME).exists():
        print("Creating config file.")
        create_config_file(path)
    with open(Path(path / CONFIG_JSON_FILENAME).resolve().as_posix(), "r") as file:
        data = json.load(file)
    if not data:
        print("Config file is empty. Creating new config file.")
        create_config_file(path, force=True)
    with open(Path(path / CONFIG_JSON_FILENAME).resolve().as_posix(), "r") as file:
        data = json.load(file)
    return data


def save_config_file(config: dict, path: str = "."):
    config_path = Path(Path(path) / CONFIG_JSON_FILENAME)
    with open(config_path.resolve().as_posix(), "w") as file:
        json.dump(config, file, indent=4)


def update_config_file(config: dict = None, path: str = "."):
    if not config:
        config = load_config_file(path)
    if config.get("CONFIG_VERSION") != DEFAULT_CONFIG.get("CONFIG_VERSION"):
        new_config = DEFAULT_CONFIG.copy().update(config)
        save_config_file(new_config, path)
        print(f"Config file updated to v{DEFAULT_CONFIG.get('CONFIG_VERSION')}.")
    else:
        print(f"Config file is already up to date (v{config.get('CONFIG_VERSION')}).")


def load_function(script_path, function_name):
    module_name = script_path.replace("/", "_").replace("\\", "_").replace(".py", "")

    # Load the module from the given path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    # Get the function from the module
    if hasattr(module, function_name):
        return getattr(module, function_name)
    else:
        raise AttributeError(f"Function '{function_name}' not found in '{script_path}'")


def run_custom_script(script_path, function_name, *args, **kwargs):
    func = load_function(script_path, function_name)
    return func(*args, **kwargs)
