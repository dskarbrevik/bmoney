"""Test that CUSTOM_CAT is preserved when toggling SHARED field"""

import pandas as pd
import numpy as np
from bmoney.utils.data import apply_custom_cat


def test_custom_cat_preserved_when_toggling_shared():
    """Test that CUSTOM_CAT is preserved when SHARED is toggled (LATEST_UPDATE is set)"""
    # Create a sample dataframe with edited rows (LATEST_UPDATE set)
    df = pd.DataFrame(
        {
            "Category": ["Groceries", "Transportation", "Entertainment"],
            "CUSTOM_CAT": ["Food & Dining", "Travel", "Fun Stuff"],
            "LATEST_UPDATE": [1234567890, 1234567891, None],  # First two are edited
        }
    )

    result = apply_custom_cat(df)

    # For edited rows, CUSTOM_CAT should be preserved
    assert result.loc[0, "CUSTOM_CAT"] == "Food & Dining"
    assert result.loc[1, "CUSTOM_CAT"] == "Travel"
    # For non-edited rows, it should map from Category
    assert result.loc[2, "CUSTOM_CAT"] in [
        "Entertainment",
        "UNKNOWN",
    ]  # Depends on CAT_MAP


def test_custom_cat_empty_string_with_edit():
    """Test that empty CUSTOM_CAT with LATEST_UPDATE falls back to Category mapping"""
    df = pd.DataFrame(
        {
            "Category": ["Groceries", "Transportation"],
            "CUSTOM_CAT": ["", ""],  # Empty strings
            "LATEST_UPDATE": [1234567890, 1234567891],  # Both edited
        }
    )

    result = apply_custom_cat(df)

    # Should fall back to Category mapping when CUSTOM_CAT is empty but row is edited
    # The actual mapping depends on the config, but it should not be empty
    assert result.loc[0, "CUSTOM_CAT"] != ""
    assert result.loc[1, "CUSTOM_CAT"] != ""


def test_custom_cat_none_with_edit():
    """Test that None CUSTOM_CAT with LATEST_UPDATE falls back to Category mapping"""
    df = pd.DataFrame(
        {
            "Category": ["Groceries", "Transportation"],
            "CUSTOM_CAT": [None, None],
            "LATEST_UPDATE": [1234567890, 1234567891],
        }
    )

    result = apply_custom_cat(df)

    # Should fall back to Category mapping when CUSTOM_CAT is None
    assert pd.notna(result.loc[0, "CUSTOM_CAT"])
    assert pd.notna(result.loc[1, "CUSTOM_CAT"])


def test_custom_cat_whitespace_only():
    """Test that whitespace-only CUSTOM_CAT is treated as empty"""
    df = pd.DataFrame(
        {
            "Category": ["Groceries"],
            "CUSTOM_CAT": ["   "],  # Whitespace only
            "LATEST_UPDATE": [1234567890],
        }
    )

    result = apply_custom_cat(df)

    # Should fall back to Category mapping for whitespace-only strings
    assert result.loc[0, "CUSTOM_CAT"].strip() != ""
    assert result.loc[0, "CUSTOM_CAT"] != "   "


def test_custom_cat_no_latest_update():
    """Test that rows without LATEST_UPDATE use Category mapping"""
    df = pd.DataFrame(
        {
            "Category": ["Groceries", "Transportation"],
            "CUSTOM_CAT": ["Should Be Ignored", "Also Ignored"],
            "LATEST_UPDATE": [None, np.nan],
        }
    )

    result = apply_custom_cat(df)

    # Without LATEST_UPDATE, should always map from Category regardless of CUSTOM_CAT
    # The CUSTOM_CAT should be overwritten with mapped value from Category
    assert result.loc[0, "CUSTOM_CAT"] != "Should Be Ignored"
    assert result.loc[1, "CUSTOM_CAT"] != "Also Ignored"
    # Should not be empty or None
    assert pd.notna(result.loc[0, "CUSTOM_CAT"])
    assert pd.notna(result.loc[1, "CUSTOM_CAT"])
