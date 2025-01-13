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
    "Pets": "PET",
    "Investment": "BANK TRANS",
    "Software & Tech": "OTHER",
    "Travel & Vacation": "TRAVEL",
    "Health & Wellness": "OTHER",
    "Personal Care": "OTHER",
    "Loan Payment": "OTHER",
    "Medical": "UNKNOWN",
    "Home & Garden": "UNKNOWN",
    "Gifts": "UNKNOWN",
    "Fees": "UNKNOWN",
    "Family Care": "UNKNOWN",
    "Education": "UNKNOWN",
    "Charitable Donations": "UNKNOWN",
    "Cash & Checks": "UNKNOWN",
    "Business": "UNKNOWN"
}

SHARED_EXPENSES = ["FOOD", 
                   "SERVICES", 
                   "TRAVEL", 
                   "CAR",
                   "PET"]

DATA_VIEW_COLS = ["Original Date",
                  "Account Name", 
                  "Institution Name", 
                  "Name",
                  "Amount",
                  "Category",
                  "Note",
                  "CUSTOM_CAT",
                  "SHARED"]