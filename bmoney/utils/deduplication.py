"""
Transaction deduplication utilities for bmoney.

This module handles identifying and removing duplicate transactions that can occur when:
- Pending transactions later post with slightly different amounts or dates
- Transaction exports overlap in time ranges
- Banks retroactively adjust transaction dates
"""

import pandas as pd
import numpy as np
from typing import Tuple
from datetime import timedelta
import hashlib


def generate_transaction_id(row: pd.Series) -> str:
    """Generates a deterministic hash ID for a transaction.

    Uses Date, Name, Amount, and Account Number to create a unique ID.
    """
    # Normalize fields
    date_str = pd.to_datetime(row["Date"]).strftime("%Y-%m-%d")
    name_str = str(row["Name"]).strip().lower() if pd.notna(row["Name"]) else ""
    amount_str = str(round(float(row["Amount"]), 2))
    account_str = str(row["Account Number"]) if pd.notna(row["Account Number"]) else ""

    # Create hash input
    hash_input = f"{date_str}|{name_str}|{amount_str}|{account_str}"

    return hashlib.sha256(hash_input.encode()).hexdigest()


def create_transaction_key(row: pd.Series) -> str:
    """
    Creates a composite key for a transaction.

    Args:
        row: A transaction row from the dataframe

    Returns:
        A string key that uniquely identifies this transaction
    """
    # Normalize the amount to avoid floating point issues
    amount = round(float(row["Amount"]), 2)

    # Create a normalized name (remove extra spaces, lowercase)
    name = str(row["Name"]).strip().lower() if pd.notna(row["Name"]) else ""

    # Use account number to differentiate same transaction on different accounts
    account = str(row["Account Number"]) if pd.notna(row["Account Number"]) else ""

    # Date as string
    date = pd.to_datetime(row["Date"]).strftime("%Y-%m-%d")

    return f"{date}|{name}|{amount}|{account}"


def find_fuzzy_duplicates(
    df: pd.DataFrame,
    date_window: int = 7,
    amount_tolerance: float = 0.50,
    comparison_mode: str = "all",
) -> pd.DataFrame:
    """
    Identifies potential duplicate transactions using fuzzy matching.

    This handles cases where:
    - Same transaction appears on slightly different dates (pending -> posted)
    - Amount changes slightly between pending and final

    Args:
        df: Transaction dataframe
        date_window: Number of days to look forward/backward for duplicates
        amount_tolerance: Maximum dollar difference to consider amounts "the same"
        comparison_mode: 'all' checks all vs all, 'existing_vs_new' only flags new duplicates of existing

    Returns:
        DataFrame with an additional 'DUPLICATE_GROUP' column
    """
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    # Initialize duplicate group column
    df["DUPLICATE_GROUP"] = -1
    group_id = 0

    for idx in range(len(df)):
        if df.loc[idx, "DUPLICATE_GROUP"] != -1:
            continue  # Already assigned to a group

        current = df.loc[idx]

        # Look for similar transactions within the date window
        date_min = current["Date"] - timedelta(days=date_window)
        date_max = current["Date"] + timedelta(days=date_window)

        # Handle Account Number matching (including NaNs)
        if pd.isna(current["Account Number"]):
            account_match = df["Account Number"].isna()
        else:
            account_match = df["Account Number"] == current["Account Number"]

        # Find candidates
        candidates = df[
            (df["Date"] >= date_min)
            & (df["Date"] <= date_max)
            & (df["Name"] == current["Name"])
            & account_match
            & (df.index != idx)
        ]

        # Check amount similarity
        similar = candidates[
            np.abs(candidates["Amount"] - current["Amount"]) <= amount_tolerance
        ]

        # If in existing_vs_new mode, only group if comparing existing vs new
        if comparison_mode == "existing_vs_new" and len(similar) > 0:
            # Only create a group if we have an existing transaction and a new one
            current_is_existing = current.get("_IS_EXISTING", False)
            similar_has_existing = (
                similar["_IS_EXISTING"].any()
                if "_IS_EXISTING" in similar.columns
                else False
            )
            similar_has_new = (
                (~similar["_IS_EXISTING"]).any()
                if "_IS_EXISTING" in similar.columns
                else True
            )

            # Only group if we're comparing existing with new (not new with new)
            if (current_is_existing and similar_has_new) or (
                not current_is_existing and similar_has_existing
            ):
                df.loc[idx, "DUPLICATE_GROUP"] = group_id
                df.loc[similar.index, "DUPLICATE_GROUP"] = group_id
                group_id += 1
        elif comparison_mode == "all" and len(similar) > 0:
            # Original behavior: group all similar transactions
            df.loc[idx, "DUPLICATE_GROUP"] = group_id
            df.loc[similar.index, "DUPLICATE_GROUP"] = group_id
            group_id += 1

    return df


def resolve_duplicates(df: pd.DataFrame, strategy: str = "keep_latest") -> pd.DataFrame:
    """
    Resolves duplicate transactions by keeping the best version.

    Args:
        df: Transaction dataframe with DUPLICATE_GROUP column
        strategy: How to resolve duplicates. Options:
            - 'keep_latest': Keep the transaction with the most recent 'Original Date'
            - 'keep_largest': Keep the transaction with the largest absolute amount
            - 'keep_existing': Prefer transactions that already have BMONEY_TRANS_ID

    Returns:
        Deduplicated dataframe
    """
    df = df.copy()

    # Separate non-duplicates from duplicates
    non_dupes = df[df["DUPLICATE_GROUP"] == -1].copy()
    dupes = df[df["DUPLICATE_GROUP"] != -1].copy()

    if len(dupes) == 0:
        return non_dupes

    # Process each duplicate group
    keep_indices = []

    for group_id in dupes["DUPLICATE_GROUP"].unique():
        group = dupes[dupes["DUPLICATE_GROUP"] == group_id].copy()

        if strategy == "keep_latest":
            # Keep the one with the most recent Original Date
            # This assumes the final/posted version comes later
            group["OriginalDateDT"] = pd.to_datetime(group["Original Date"])
            idx_to_keep = group["OriginalDateDT"].idxmax()

        elif strategy == "keep_largest":
            # Keep the one with largest absolute amount (final might be larger)
            idx_to_keep = group["Amount"].abs().idxmax()

        elif strategy == "keep_existing":
            # Prefer transactions that already exist (have BMONEY_TRANS_ID)
            has_id = group[group["BMONEY_TRANS_ID"].notna()].copy()
            if len(has_id) > 0:
                # If multiple have IDs, use latest
                has_id["OriginalDateDT"] = pd.to_datetime(has_id["Original Date"])
                idx_to_keep = has_id["OriginalDateDT"].idxmax()
            else:
                # Otherwise use latest
                group["OriginalDateDT"] = pd.to_datetime(group["Original Date"])
                idx_to_keep = group["OriginalDateDT"].idxmax()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        keep_indices.append(idx_to_keep)

    # Combine non-duplicates with resolved duplicates
    resolved = pd.concat([non_dupes, dupes.loc[keep_indices]])

    # Drop the temporary DUPLICATE_GROUP column
    resolved = resolved.drop(columns=["DUPLICATE_GROUP"])

    return resolved.sort_values("Date").reset_index(drop=True)


def deduplicate_transactions(
    df: pd.DataFrame,
    date_window: int = 7,
    amount_tolerance: float = 0.50,
    strategy: str = "keep_latest",
    verbose: bool = False,
    comparison_mode: str = "all",
) -> Tuple[pd.DataFrame, dict]:
    """
    Main deduplication function that finds and resolves duplicate transactions.

    Args:
        df: Transaction dataframe
        date_window: Days to look for potential duplicates
        amount_tolerance: Dollar tolerance for fuzzy amount matching
        strategy: How to resolve duplicates ('keep_latest', 'keep_largest', 'keep_existing')
        verbose: Whether to print statistics
        comparison_mode: 'all' checks all vs all, 'existing_vs_new' only deduplicates new against existing

    Returns:
        Tuple of (deduplicated dataframe, statistics dict)
    """
    original_count = len(df)

    # Find duplicates
    df_with_groups = find_fuzzy_duplicates(
        df, date_window, amount_tolerance, comparison_mode
    )

    # Count duplicates found
    num_duplicates = len(df_with_groups[df_with_groups["DUPLICATE_GROUP"] != -1])
    num_groups = df_with_groups["DUPLICATE_GROUP"].nunique() - 1  # -1 for the -1 group

    # Resolve duplicates
    df_clean = resolve_duplicates(df_with_groups, strategy)

    final_count = len(df_clean)
    removed_count = original_count - final_count

    stats = {
        "original_count": original_count,
        "final_count": final_count,
        "removed_count": removed_count,
        "duplicate_groups": num_groups,
        "transactions_in_groups": num_duplicates,
    }

    if verbose:
        print("\nDeduplication Results:")
        print(f"  Original transactions: {original_count}")
        print(f"  Duplicate groups found: {num_groups}")
        print(f"  Transactions in duplicate groups: {num_duplicates}")
        print(f"  Duplicates removed: {removed_count}")
        print(f"  Final transaction count: {final_count}")

    return df_clean, stats


def merge_new_transactions(
    master_df: pd.DataFrame,
    new_df: pd.DataFrame,
    date_window: int = 7,
    amount_tolerance: float = 0.50,
    verbose: bool = False,
) -> Tuple[pd.DataFrame, dict]:
    """
    Merges new transactions into master dataframe with intelligent deduplication.

    This approach ONLY deduplicates new transactions against existing ones, NOT
    new transactions against each other. This allows multiple similar purchases
    (e.g., 2 coffees at Starbucks on the same day) to both be added from a single
    export, while still preventing the same transaction from being added twice
    from different exports.

    Args:
        master_df: Existing master transaction dataframe
        new_df: New transactions to merge in
        date_window: Days to look for potential duplicates
        amount_tolerance: Dollar tolerance for fuzzy matching
        verbose: Whether to print progress

    Returns:
        Tuple of (merged deduplicated dataframe, statistics dict)
    """
    if verbose:
        print(f"Master transactions: {len(master_df)}")
        print(f"New transactions: {len(new_df)}")

    # Mark which transactions are from master (existing)
    # This helps us only deduplicate new against existing, not new against new
    master_df = master_df.copy()
    new_df = new_df.copy()

    # Ensure REMOVED column exists in master_df
    if "REMOVED" not in master_df.columns:
        master_df["REMOVED"] = False
    else:
        master_df["REMOVED"] = master_df["REMOVED"].fillna(False).astype(bool)

    # Filter out new transactions that match existing IDs (including removed ones)
    id_duplicates_removed = 0
    initial_new_count = len(new_df)

    if "BMONEY_TRANS_ID" in master_df.columns:
        # Generate IDs for new transactions
        new_df["BMONEY_TRANS_ID"] = new_df.apply(generate_transaction_id, axis=1)

        existing_ids = set(master_df["BMONEY_TRANS_ID"].dropna())
        new_df = new_df[~new_df["BMONEY_TRANS_ID"].isin(existing_ids)].copy()
        id_duplicates_removed = initial_new_count - len(new_df)

        if verbose and id_duplicates_removed > 0:
            print(
                f"Removed {id_duplicates_removed} transactions that matched existing IDs (including deleted ones)."
            )

    master_df["_IS_EXISTING"] = True
    new_df["_IS_EXISTING"] = False

    # Combine all transactions
    combined = pd.concat([master_df, new_df], ignore_index=True)

    # Deduplicate using existing_vs_new mode - only removes duplicates between existing and new
    # This preserves multiple similar transactions within the new export
    df_clean, stats = deduplicate_transactions(
        combined,
        date_window=date_window,
        amount_tolerance=amount_tolerance,
        strategy="keep_existing",  # Prefer existing transactions
        verbose=verbose,
        comparison_mode="existing_vs_new",  # Only deduplicate new vs existing, not new vs new
    )

    # Remove the temporary marker column
    if "_IS_EXISTING" in df_clean.columns:
        df_clean = df_clean.drop(columns=["_IS_EXISTING"])

    # Calculate how many new transactions were actually added
    transactions_added = stats["final_count"] - len(master_df)
    stats["transactions_added"] = transactions_added

    # Update stats to include ID-based removals
    stats["removed_count"] += id_duplicates_removed
    stats["id_duplicates_removed"] = id_duplicates_removed

    return df_clean, stats
