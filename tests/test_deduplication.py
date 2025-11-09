#!/usr/bin/env python3
"""
Test script for the new deduplication functionality.

This script demonstrates how the new deduplication approach handles:
1. Exact duplicates
2. Pending -> Posted transactions (amount changes)
3. Date shifts (weekend transactions posting on Monday)
4. Retroactive date adjustments
"""

import pandas as pd
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from bmoney.utils.deduplication import (
    deduplicate_transactions,
    merge_new_transactions,
)


def create_sample_data_with_duplicates():
    """Create sample transaction data with various duplicate scenarios."""

    transactions = [
        # Scenario 1: Exact duplicate
        {
            "Date": "2025-01-15",
            "Original Date": "2025-01-15",
            "Account Number": 1234,
            "Name": "Amazon.com",
            "Amount": 49.99,
            "Category": "Shopping",
            "Note": "",
        },
        {
            "Date": "2025-01-15",
            "Original Date": "2025-01-15",
            "Account Number": 1234,
            "Name": "Amazon.com",
            "Amount": 49.99,
            "Category": "Shopping",
            "Note": "",
        },
        # Scenario 2: Pending -> Posted (amount changed)
        {
            "Date": "2025-01-20",
            "Original Date": "2025-01-20",
            "Account Number": 5678,
            "Name": "Whole Foods",
            "Amount": 125.00,  # Pending amount
            "Category": "Groceries",
            "Note": "",
        },
        {
            "Date": "2025-01-22",
            "Original Date": "2025-01-22",
            "Account Number": 5678,
            "Name": "Whole Foods",
            "Amount": 124.87,  # Final posted amount
            "Category": "Groceries",
            "Note": "",
        },
        # Scenario 3: Weekend transaction posting on Monday
        {
            "Date": "2025-01-25",  # Saturday
            "Original Date": "2025-01-25",
            "Account Number": 9012,
            "Name": "Chevron",
            "Amount": 55.00,
            "Category": "Auto & Transport",
            "Note": "",
        },
        {
            "Date": "2025-01-27",  # Monday (same transaction, date adjusted)
            "Original Date": "2025-01-27",
            "Account Number": 9012,
            "Name": "Chevron",
            "Amount": 55.00,
            "Category": "Auto & Transport",
            "Note": "",
        },
        # Scenario 4: Different transactions - should NOT be duplicates
        {
            "Date": "2025-01-28",
            "Original Date": "2025-01-28",
            "Account Number": 1234,
            "Name": "Starbucks",
            "Amount": 5.75,
            "Category": "Dining & Drinks",
            "Note": "",
        },
        {
            "Date": "2025-01-29",
            "Original Date": "2025-01-29",
            "Account Number": 1234,
            "Name": "Starbucks",
            "Amount": 5.75,
            "Category": "Dining & Drinks",
            "Note": "",
        },
    ]

    df = pd.DataFrame(transactions)
    df["Date"] = pd.to_datetime(df["Date"])
    df["BMONEY_TRANS_ID"] = None  # Will be assigned by apply_transformations

    return df


def test_exact_duplicates():
    """Test detection of exact duplicate transactions."""
    print("\n" + "=" * 70)
    print("TEST 1: Exact Duplicates")
    print("=" * 70)

    data = [
        {
            "Date": "2025-01-15",
            "Name": "Amazon",
            "Amount": 50.00,
            "Account Number": 1234,
        },
        {
            "Date": "2025-01-15",
            "Name": "Amazon",
            "Amount": 50.00,
            "Account Number": 1234,
        },
    ]
    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Original Date"] = df["Date"]
    df["BMONEY_TRANS_ID"] = None

    print(f"\nOriginal transactions: {len(df)}")
    print(df[["Date", "Name", "Amount"]])

    df_clean, stats = deduplicate_transactions(df, verbose=True)

    print(f"\nAfter deduplication: {len(df_clean)}")
    print(df_clean[["Date", "Name", "Amount"]])

    assert len(df_clean) == 1, "Should have removed exact duplicate"
    print("\n✅ Test passed!")


def test_pending_to_posted():
    """Test detection of pending -> posted transaction changes."""
    print("\n" + "=" * 70)
    print("TEST 2: Pending -> Posted (Amount Change)")
    print("=" * 70)

    data = [
        {
            "Date": "2025-01-20",
            "Original Date": "2025-01-20",
            "Name": "Whole Foods",
            "Amount": 125.00,
            "Account Number": 5678,
        },  # Pending
        {
            "Date": "2025-01-22",
            "Original Date": "2025-01-22",
            "Name": "Whole Foods",
            "Amount": 124.87,
            "Account Number": 5678,
        },  # Posted (final)
    ]
    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["Date"])
    df["BMONEY_TRANS_ID"] = None

    print(f"\nOriginal transactions: {len(df)}")
    print(df[["Date", "Original Date", "Name", "Amount"]])

    # Use amount tolerance of $0.50 to catch these
    df_clean, stats = deduplicate_transactions(df, amount_tolerance=0.50, verbose=True)

    print(f"\nAfter deduplication: {len(df_clean)}")
    print(df_clean[["Date", "Original Date", "Name", "Amount"]])

    assert len(df_clean) == 1, "Should have detected pending->posted as duplicate"
    # Should keep the later one (posted version)
    assert df_clean.iloc[0]["Amount"] == 124.87, (
        "Should keep the posted (later) version"
    )
    print("\n✅ Test passed!")


def test_date_shift():
    """Test detection of transactions that shift dates."""
    print("\n" + "=" * 70)
    print("TEST 3: Date Shift (Weekend -> Monday)")
    print("=" * 70)

    data = [
        {
            "Date": "2025-01-25",
            "Original Date": "2025-01-25",
            "Name": "Chevron",
            "Amount": 55.00,
            "Account Number": 9012,
        },  # Saturday
        {
            "Date": "2025-01-27",
            "Original Date": "2025-01-27",
            "Name": "Chevron",
            "Amount": 55.00,
            "Account Number": 9012,
        },  # Monday (adjusted)
    ]
    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["Date"])
    df["BMONEY_TRANS_ID"] = None

    print(f"\nOriginal transactions: {len(df)}")
    print(df[["Date", "Original Date", "Name", "Amount"]])

    df_clean, stats = deduplicate_transactions(df, date_window=7, verbose=True)

    print(f"\nAfter deduplication: {len(df_clean)}")
    print(df_clean[["Date", "Original Date", "Name", "Amount"]])

    assert len(df_clean) == 1, "Should have detected date-shifted duplicate"
    print("\n✅ Test passed!")


def test_non_duplicates():
    """Test that similar but different transactions are NOT marked as duplicates."""
    print("\n" + "=" * 70)
    print("TEST 4: Non-Duplicates (Multiple Starbucks visits)")
    print("=" * 70)

    data = [
        {
            "Date": "2025-01-28",
            "Original Date": "2025-01-28",
            "Name": "Starbucks",
            "Amount": 5.75,
            "Account Number": 1234,
        },
        {
            "Date": "2025-01-29",
            "Original Date": "2025-01-29",
            "Name": "Starbucks",
            "Amount": 5.75,
            "Account Number": 1234,
        },
    ]
    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["Date"])
    df["BMONEY_TRANS_ID"] = None

    print(f"\nOriginal transactions: {len(df)}")
    print(df[["Date", "Original Date", "Name", "Amount"]])

    # With date_window=0, these won't be considered duplicates
    df_clean, stats = deduplicate_transactions(df, date_window=0, verbose=True)

    print(f"\nAfter deduplication: {len(df_clean)}")
    print(df_clean[["Date", "Original Date", "Name", "Amount"]])

    assert len(df_clean) == 2, "Should NOT mark separate transactions as duplicates"
    print("\n✅ Test passed!")


def test_merge_scenario():
    """Test merging new transactions into existing master."""
    print("\n" + "=" * 70)
    print("TEST 5: Merge New Transactions (Real-world scenario)")
    print("=" * 70)

    # Simulate existing master data
    master_data = [
        {
            "Date": "2025-01-15",
            "Original Date": "2025-01-15",
            "Name": "Amazon",
            "Amount": 49.99,
            "Account Number": 1234,
            "BMONEY_TRANS_ID": "existing-1",
        },
        {
            "Date": "2025-01-20",
            "Original Date": "2025-01-20",
            "Name": "Whole Foods",
            "Amount": 125.00,
            "Account Number": 5678,
            "BMONEY_TRANS_ID": "existing-2",
        },  # Pending
    ]
    master_df = pd.DataFrame(master_data)
    master_df["Date"] = pd.to_datetime(master_df["Date"])

    # Simulate new CSV export (includes some duplicates and new transactions)
    new_data = [
        # Duplicate of existing transaction
        {
            "Date": "2025-01-15",
            "Original Date": "2025-01-15",
            "Name": "Amazon",
            "Amount": 49.99,
            "Account Number": 1234,
            "BMONEY_TRANS_ID": None,
        },
        # Final posted version of pending transaction (amount changed)
        {
            "Date": "2025-01-22",
            "Original Date": "2025-01-22",
            "Name": "Whole Foods",
            "Amount": 124.87,
            "Account Number": 5678,
            "BMONEY_TRANS_ID": None,
        },
        # Completely new transaction
        {
            "Date": "2025-01-25",
            "Original Date": "2025-01-25",
            "Name": "Target",
            "Amount": 87.50,
            "Account Number": 1234,
            "BMONEY_TRANS_ID": None,
        },
    ]
    new_df = pd.DataFrame(new_data)
    new_df["Date"] = pd.to_datetime(new_df["Date"])

    print(f"\nMaster transactions: {len(master_df)}")
    print(master_df[["Date", "Name", "Amount", "BMONEY_TRANS_ID"]])

    print(f"\nNew transactions from CSV: {len(new_df)}")
    print(new_df[["Date", "Name", "Amount"]])

    merged_df, stats = merge_new_transactions(
        master_df=master_df,
        new_df=new_df,
        date_window=7,
        amount_tolerance=0.50,
        verbose=True,
    )

    print(f"\nFinal merged transactions: {len(merged_df)}")
    print(merged_df[["Date", "Name", "Amount", "BMONEY_TRANS_ID"]])

    # Should have 3 transactions total:
    # 1. Amazon (kept from master)
    # 2. Whole Foods (updated to posted version)
    # 3. Target (new)
    assert len(merged_df) == 3, f"Should have 3 transactions, got {len(merged_df)}"

    # Check that we kept the existing transaction ID for Amazon
    amazon = merged_df[merged_df["Name"] == "Amazon"]
    assert amazon.iloc[0]["BMONEY_TRANS_ID"] == "existing-1", (
        "Should preserve existing ID"
    )

    print("\n✅ Test passed!")


def run_all_tests():
    """Run all deduplication tests."""
    print("\n" + "=" * 70)
    print("BMONEY DEDUPLICATION TEST SUITE")
    print("=" * 70)

    try:
        test_exact_duplicates()
        test_pending_to_posted()
        test_date_shift()
        test_non_duplicates()
        test_merge_scenario()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nThe new deduplication system is working correctly!")
        print("\nKey features validated:")
        print("  ✓ Removes exact duplicates")
        print("  ✓ Detects pending -> posted transitions")
        print("  ✓ Handles date-shifted transactions")
        print("  ✓ Preserves distinct transactions")
        print("  ✓ Intelligently merges new data with existing")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
