"""
Constants used by other functions.
"""

MASTER_DF_FILENAME = "BUDGET_MONEY_TRANSACTIONS.jsonl"

CAT_MAP = {
    "Groceries": "FOOD",
    "Auto & Transport": "CAR",
    "Dining & Drinks": "FOOD",
    "Credit Card Payment": "BANK TRANS",
    "Uncategorized": "UNKNOWN",
    "Shopping": "OTHER",
    "Income": "INCOME",
    "Bills & Utilities": "OTHER",
    "Entertainment & Rec.": "SERVICES",
    "Internal Transfers": "BANK TRANS",
    "Pets": "SERVICES",
    "Investment": "BANK TRANS",
    "Software & Tech": "OTHER",
    "Travel & Vacation": "TRAVEL",
    "Health & Wellness": "OTHER",
    "Personal Care": "OTHER",
    "Loan Payment": "OTHER",
}

SHARED_EXPENSES = ["FOOD", "SERVICES", "TRAVEL", "CAR"]
