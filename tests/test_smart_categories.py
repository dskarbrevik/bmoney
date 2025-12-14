"""Test smart categorization feature"""

import pandas as pd
from datetime import datetime
from bmoney.utils.data import apply_smart_categories, apply_transformations


def test_smart_categories_learns_from_historical_transactions():
    """Test that smart_categories learns from historical transactions with same Name"""
    # Create master dataframe with historical transactions
    master_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 1, 1), datetime(2025, 1, 15)],
            "Name": ["Starbucks Coffee", "Target Store"],
            "Category": ["Dining", "Shopping"],
            "Amount": [5.50, 45.99],
            "CUSTOM_CAT": ["Coffee & Tea", "Groceries"],
            "LATEST_UPDATE": [1234567890, 1234567891],  # Both manually edited
        }
    )

    # Create new transactions with same names
    new_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 2, 1), datetime(2025, 2, 2)],
            "Name": ["Starbucks Coffee", "Target Store"],
            "Category": ["Dining", "Shopping"],
            "Amount": [6.00, 32.50],
            "CUSTOM_CAT": [None, None],
            "LATEST_UPDATE": [None, None],  # Not edited yet
        }
    )

    result = apply_smart_categories(new_df, master_df)

    # Should learn from historical transactions
    assert result.loc[0, "CUSTOM_CAT"] == "Coffee & Tea"
    assert result.loc[1, "CUSTOM_CAT"] == "Groceries"


def test_smart_categories_uses_most_recent_match():
    """Test that smart_categories uses the most recent CUSTOM_CAT when multiple matches exist"""
    # Create master dataframe with multiple entries for same Name
    master_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 1, 1), datetime(2025, 1, 15), datetime(2025, 2, 1)],
            "Name": ["Amazon", "Amazon", "Amazon"],
            "Category": ["Shopping", "Shopping", "Shopping"],
            "Amount": [25.99, 42.00, 15.50],
            "CUSTOM_CAT": ["Electronics", "Books", "Household"],  # Changed over time
            "LATEST_UPDATE": [1234567890, 1234567891, 1234567892],
        }
    )

    # Create new transaction
    new_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 3, 1)],
            "Name": ["Amazon"],
            "Category": ["Shopping"],
            "Amount": [30.00],
            "CUSTOM_CAT": [None],
            "LATEST_UPDATE": [None],
        }
    )

    result = apply_smart_categories(new_df, master_df)

    # Should use the most recent categorization (Household from Feb 1)
    assert result.loc[0, "CUSTOM_CAT"] == "Household"


def test_smart_categories_fallback_to_category_mapping():
    """Test that smart_categories falls back to Category mapping when no Name match found"""
    # Create master dataframe with unrelated transactions
    master_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 1, 1)],
            "Name": ["Starbucks Coffee"],
            "Category": ["Dining"],
            "Amount": [5.50],
            "CUSTOM_CAT": ["Coffee & Tea"],
            "LATEST_UPDATE": [1234567890],
        }
    )

    # Create new transaction with different Name
    new_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 2, 1)],
            "Name": ["New Restaurant"],
            "Category": ["Groceries"],  # Has standard category
            "Amount": [25.00],
            "CUSTOM_CAT": [None],
            "LATEST_UPDATE": [None],
        }
    )

    result = apply_smart_categories(new_df, master_df)

    # Should fall back to Category mapping (depends on CAT_MAP config)
    # The exact value depends on config, but should not be None
    assert pd.notna(result.loc[0, "CUSTOM_CAT"])
    assert result.loc[0, "CUSTOM_CAT"] != ""


def test_smart_categories_preserves_edited_transactions():
    """Test that smart_categories preserves CUSTOM_CAT for already edited transactions"""
    master_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 1, 1)],
            "Name": ["Starbucks Coffee"],
            "Category": ["Dining"],
            "Amount": [5.50],
            "CUSTOM_CAT": ["Coffee & Tea"],
            "LATEST_UPDATE": [1234567890],
        }
    )

    # Create transaction that's already been edited
    new_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 2, 1)],
            "Name": ["Starbucks Coffee"],
            "Category": ["Dining"],
            "Amount": [6.00],
            "CUSTOM_CAT": ["My Custom Category"],
            "LATEST_UPDATE": [1234567892],  # Already edited
        }
    )

    result = apply_smart_categories(new_df, master_df)

    # Should preserve the edited CUSTOM_CAT, not override with historical match
    assert result.loc[0, "CUSTOM_CAT"] == "My Custom Category"


def test_smart_categories_ignores_unedited_master_transactions():
    """Test that smart_categories only learns from edited transactions in master"""
    # Create master with both edited and unedited transactions
    master_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 1, 1), datetime(2025, 1, 15)],
            "Name": ["Starbucks Coffee", "Starbucks Coffee"],
            "Category": ["Dining", "Dining"],
            "Amount": [5.50, 6.00],
            "CUSTOM_CAT": ["Should Be Ignored", "Coffee & Tea"],
            "LATEST_UPDATE": [None, 1234567891],  # First is not edited
        }
    )

    new_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 2, 1)],
            "Name": ["Starbucks Coffee"],
            "Category": ["Dining"],
            "Amount": [6.50],
            "CUSTOM_CAT": [None],
            "LATEST_UPDATE": [None],
        }
    )

    result = apply_smart_categories(new_df, master_df)

    # Should use the edited transaction's category, not the unedited one
    assert result.loc[0, "CUSTOM_CAT"] == "Coffee & Tea"


def test_smart_categories_handles_empty_master():
    """Test that smart_categories handles empty master dataframe gracefully"""
    master_df = pd.DataFrame()

    new_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 2, 1)],
            "Name": ["Some Store"],
            "Category": ["Shopping"],
            "Amount": [25.00],
            "CUSTOM_CAT": [None],
            "LATEST_UPDATE": [None],
        }
    )

    result = apply_smart_categories(new_df, master_df)

    # Should fall back to Category mapping
    assert pd.notna(result.loc[0, "CUSTOM_CAT"])


def test_smart_categories_ignores_unknown_categories_in_master():
    """Test that smart_categories doesn't learn from UNKNOWN categories"""
    master_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 1, 1), datetime(2025, 1, 15)],
            "Name": ["Mystery Store", "Mystery Store"],
            "Category": ["Unknown", "Shopping"],
            "Amount": [10.00, 15.00],
            "CUSTOM_CAT": ["UNKNOWN", "Retail"],
            "LATEST_UPDATE": [1234567890, 1234567891],
        }
    )

    new_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 2, 1)],
            "Name": ["Mystery Store"],
            "Category": ["Shopping"],
            "Amount": [20.00],
            "CUSTOM_CAT": [None],
            "LATEST_UPDATE": [None],
        }
    )

    result = apply_smart_categories(new_df, master_df)

    # Should use 'Retail' and ignore 'UNKNOWN' even though it's more recent
    assert result.loc[0, "CUSTOM_CAT"] == "Retail"


def test_smart_categories_handles_missing_name_field():
    """Test that smart_categories handles transactions with missing Name field"""
    master_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 1, 1)],
            "Name": ["Some Store"],
            "Category": ["Shopping"],
            "Amount": [25.00],
            "CUSTOM_CAT": ["Retail"],
            "LATEST_UPDATE": [1234567890],
        }
    )

    new_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 2, 1)],
            "Name": [None],  # Missing name
            "Category": ["Shopping"],
            "Amount": [30.00],
            "CUSTOM_CAT": [None],
            "LATEST_UPDATE": [None],
        }
    )

    result = apply_smart_categories(new_df, master_df)

    # Should fall back to Category mapping
    assert pd.notna(result.loc[0, "CUSTOM_CAT"])


def test_apply_transformations_with_smart_categories():
    """Test that apply_transformations correctly uses smart_categories when enabled"""
    master_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 1, 1)],
            "Name": ["Coffee Shop"],
            "Category": ["Dining"],
            "Amount": [5.50],
            "Note": [""],
            "CUSTOM_CAT": ["Beverages"],
            "LATEST_UPDATE": [1234567890],
            "Account Number": ["1234"],
        }
    )

    new_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 2, 1)],
            "Name": ["Coffee Shop"],
            "Category": ["Dining"],
            "Amount": [6.00],
            "Note": [""],
            "Account Number": ["1234"],
        }
    )

    # Test with smart_categories enabled
    result = apply_transformations(new_df, smart_categories=True, master_df=master_df)

    assert result.loc[0, "CUSTOM_CAT"] == "Beverages"
    assert pd.notna(result.loc[0, "BMONEY_TRANS_ID"])  # UUID added
    assert pd.notna(result.loc[0, "MONTH"])  # Month added
    assert pd.notna(result.loc[0, "YEAR"])  # Year added


def test_apply_transformations_without_smart_categories():
    """Test that apply_transformations uses regular categorization when smart_categories disabled"""
    master_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 1, 1)],
            "Name": ["Coffee Shop"],
            "Category": ["Dining"],
            "Amount": [5.50],
            "Note": [""],
            "CUSTOM_CAT": ["Beverages"],
            "LATEST_UPDATE": [1234567890],
            "Account Number": ["1234"],
        }
    )

    new_df = pd.DataFrame(
        {
            "Date": [datetime(2025, 2, 1)],
            "Name": ["Coffee Shop"],
            "Category": ["Groceries"],  # Different category
            "Amount": [6.00],
            "Note": [""],
            "Account Number": ["1234"],
        }
    )

    # Test with smart_categories disabled (should use Category mapping, not learn from master)
    result = apply_transformations(new_df, smart_categories=False, master_df=master_df)

    # Should map from Category, not learn from master
    assert result.loc[0, "CUSTOM_CAT"] != "Beverages"
    assert pd.notna(result.loc[0, "CUSTOM_CAT"])
