import pytest
from unittest.mock import patch, mock_open
import pandas as pd
from pathlib import Path
from bmoney.utils.data import load_master_transaction_df

MASTER_DF_FILENAME = "BUDGET_MONEY_TRANSACTIONS.jsonl"
MOCK_DATA_PATH = "/tests/data"


@pytest.fixture
def mock_jsonl_data():
    """Fixture for mock JSONL data."""
    return '[{"Date": "2023-01-01", "Amount": 100, "Category": "Food"}]\n'


@pytest.fixture
def mock_master_path():
    """Fixture for the mock master JSONL file path."""
    return Path(MOCK_DATA_PATH).joinpath(MASTER_DF_FILENAME)


def test_load_master_transaction_df_file_exists(mock_jsonl_data, mock_master_path):
    """Test that the function loads the master file when it exists."""
    with (
        patch("builtins.open", mock_open(read_data=mock_jsonl_data)),
        patch("pandas.read_json") as mock_read_json,
        patch("pathlib.Path.exists", return_value=True),
    ):
        mock_df = pd.DataFrame(
            [{"Date": "2023-01-01", "Amount": 100, "Category": "Food"}]
        )
        mock_read_json.return_value = mock_df

        result = load_master_transaction_df(MOCK_DATA_PATH)

        mock_read_json.assert_called_once_with(
            mock_master_path, orient="records", lines=True
        )
        assert result.equals(mock_df)


def test_load_master_transaction_df_validate(mock_jsonl_data, mock_master_path):
    """Test that the function validates and saves the master file if validate=True."""
    with (
        patch("builtins.open", mock_open(read_data=mock_jsonl_data)),
        patch("pandas.read_json") as mock_read_json,
        patch("pathlib.Path.exists", return_value=True),
        patch("pandas.DataFrame.to_json") as mock_to_json,
        patch("bmoney.utils.data.apply_transformations", side_effect=lambda x: x),
    ):
        mock_df = pd.DataFrame(
            [{"Date": "2023-01-01", "Amount": 100, "Category": "Food"}]
        )
        mock_read_json.return_value = mock_df

        result = load_master_transaction_df(MOCK_DATA_PATH, validate=True)

        mock_read_json.assert_called_once_with(
            mock_master_path, orient="records", lines=True
        )
        mock_to_json.assert_any_call(mock_master_path, orient="records", lines=True)
        assert result.equals(mock_df)


def test_load_master_transaction_df_file_not_exists(mock_master_path):
    """Test that the function handles the absence of the master file."""
    with patch("pathlib.Path.exists", return_value=False):
        result = load_master_transaction_df(MOCK_DATA_PATH)
        assert result is None
