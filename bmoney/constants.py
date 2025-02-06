"""
Constants used by other functions.
"""

import importlib.metadata

PACKAGE_NAME = __name__.split(".")[0]  # ex. bmoney
CURRENT_VERSION = importlib.metadata.version(PACKAGE_NAME)  # ex. 0.1.0

# the name of the file containing your running transactions. Essentially your database.
# Over time you may have new rocket money export csvs but this file persists forever.
MASTER_DF_FILENAME = "BUDGET_MONEY_TRANSACTIONS.jsonl"

# name of config file in main project directory
CONFIG_JSON_FILENAME = "config.json"

# Maps Rocket Money categories to your own custom categories
# Here I'm using a mapping that results in fewer more high level categories to make budgeting easier
CAT_MAP = {
    "Groceries": "FOOD",
    "Auto & Transport": "CAR",
    "Dining & Drinks": "FOOD",
    "Credit Card Payment": "BANK TRANS",
    "Uncategorized": "UNKNOWN",
    "Shopping": "OTHER",
    "Income": "INCOME",
    "Bills & Utilities": "SERVICES",
    "Entertainment & Rec.": "ENTERTAINMENT",
    "Internal Transfers": "BANK TRANS",
    "Pets": "PET",
    "Investment": "BANK TRANS",
    "Software & Tech": "OTHER",
    "Travel & Vacation": "TRAVEL",
    "Health & Wellness": "OTHER",
    "Personal Care": "OTHER",
    "Loan Payment": "OTHER",
    "Medical": "OTHER",
    "Home & Garden": "HOUSEHOLD",
    "Gifts": "OTHER",
    "Fees": "OTHER",
    "Family Care": "OTHER",
    "Education": "OTHER",
    "Charitable Donations": "OTHER",
    "Cash & Checks": "OTHER",
    "Business": "OTHER",
}

# decides which CUSTOM_CAT values should have SHARED set to True
SHARED_EXPENSES = [
    "FOOD",
    "SERVICES",
    "TRAVEL",
    "CAR",
    "PET",
    "RENT",
    "ENTERTAINMENT",
    "HOUSEHOLD",
]


# decides which columns and general order to show in app's data viewer
DATA_VIEW_COLS = [
    "Date",
    "Original Date",
    "Name",
    "Amount",
    "Category",
    "CUSTOM_CAT",
    "SHARED",
    "Note",
    "Institution Name",
    "Account Name",
]

# if Note col equals this msg, SHARED will be set to True
SHARED_NOTE_MSG = "shared"

# if Note col equals this msg, SHARED will be set to False
NOT_SHARED_NOTE_MSG = "not shared"


# All columns that make up the master transaction jsonl file
MASTER_COLUMNS = [
    "Date",
    "Original Date",
    "Account Type",
    "Account Name",
    "Account Number",
    "Institution Name",
    "Name",
    "Custom Name",
    "Amount",
    "Description",
    "Category",
    "Note",
    "Ignored From",
    "Tax Deductible",
    "CUSTOM_CAT",
    "MONTH",
    "YEAR",
    "SHARED",
    "LATEST_UPDATE",
]

DEFAULT_CONFIG = {
    "CONFIG_VERSION": CURRENT_VERSION,
    "BUDGET_MONEY_USER": "",
    "MASTER_DF_FILENAME": MASTER_DF_FILENAME,
    "SHARED_EXPENSES": SHARED_EXPENSES,
    "SHARED_NOTE_MSG": SHARED_NOTE_MSG,
    "NOT_SHARED_NOTE_MSG": NOT_SHARED_NOTE_MSG,
    "CAT_MAP": CAT_MAP,
    "DATA_VIEW_COLS": DATA_VIEW_COLS,
    "GSHEETS_CONFIG": {
        "SPREADSHEET_ID": "",
        "SPREADSHEET_TABS": {
            "TRANSACTIONS": "",  # sheet for shared transactions
            "CATEGORIES": "",  # sheet for shared expense custom category monthly totals
        },
        "GCP_SERVICE_ACCOUNT_PATH": "",
    },
    "CUSTOM_WIDGETS": [],
}
