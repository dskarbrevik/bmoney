# Budget Money

Budget Money (bmoney) is a budgeting tool that builds on top of Rocket Money transaction exports.

---

Rocket Money allows users to export their financial transactions to a CSV file. Rocket Money (through their partnered service Plaid) provide transactions up to two years ago.

Budget Money (this tool) builds ontop of these CSVs:
- Merge your Rocket Money CSV exports into one highly portable master file
- Easily edit transaction data in your master file (through a locally deployed webapp)
    - Display and easily edit all your data
    - Custom Metrics and visualization dashboard to see category spending habit in more detail
- Map Rocket Money categories to your own custom categories
- Export shared transactions to Google Sheets to make sharing finances with roommates/partners easier

## Installation

`pip install bmoney`

Once `bmoney` is installed in your environment, you can navigate to a directory where you want to store your transaction data files. Make sure you have a Rocket Money transaction export CSV file in that folder before using the bmoney cmds below.

## Basic usage

1) Create a project folder and put a Rocket Money transaction export CSV file in it.

2) `bmoney init` from inside your project folder

You should see a a config.json and jsonl transaction file in your folder now.

3) `bmoney launch` to see the budget money dashboard with your data.

## Screenshots

<img src="assets/images/bmoney_app1.png" width="500" alt="bmoney dashboard">

<img src="assets/images/bmoney_app2.png" width="500" alt="bmoney data editor">


## CLI command quickstart

| name | description |
| --- | --- |
| `bmoney init` | Initialize your project folder |
| `bmoney launch` | Launch the bmoney browser app |
| `bmoney db update` | Merge any CSVs into the master JSONL file |
| `bmoney gsheets sync` | Send current data to your Google Spreadsheet |


### Explanation of config.json file

On `bmoney init` the `config.json` file comes pre-populated with many default values. The config file is a recent (v0.2.x) introduction and some variables may cause issues if they are edited in certain ways.

Below is an explanation of variables in `config.json` along with a declaration of whether I'd recommend manipulating this variable currently. Obviously all variables should be editable but this is just a toy personal project after all :)

| name | type | description | notes |
| --- | --- | --- | --- |
| MASTER_DF_FILENAME | `str` | Filename for master jsonl transactions | |
| SHARED_EXPENSES | `list(str)` | CUSTOM_CAT vals that will have `SHARED==True` in master df| |
| CAT_MAP | `dict(str)` | Mapping Rocket Money categories to your own custom categories | There is an interplay between SHARED_EXPENSES and CAT_MAP. |
| DATA_VIEW_COLS | `list(str)` | The name of master df columns to show in the app's data editor tab | |
| GSHEETS_CONFIG | `dict(str)` | Vars important for using the Google Sheets integration | |
| BUDGET_MONEY_USER | `str` | Username, this is applied to create the Person col in the master df | This will be asked on `bmoney init` if not expressly provided to that command|
| CUSTOM_WIDGETS | `list(dict)` | A list of widget config dicts to display in th dashboard. See example usage for more info. |

More about the GSHEETS_CONFIG dict:

| name | type | description | notes |
| --- | ---| --- | --- |
| SPREADSHEET_ID | `str` | The ID of your Google Sheet file | |
| SPREADSHEET_TABS | `dict` | key:val pairs for different bmoney->gsheets capabilities | Leave a Tab val as "" if you don't want to use that capability. |
| START_DATE | `str` | Optional date (`format="%m/%d/%Y"`; e.g. `"01/31/2024"`) to filter transactions that are sent to gsheets. | This can be useful if your transactions go back further in time than your use of Google Sheets as a budgeting tool. |
| GCP_SERVICE_ACCOUNT_PATH | `str` | The path to a json file containing GCP provided service account credentials. | See [here](https://support.google.com/a/answer/7378726?hl=en) for info on how to setup a GCP Service Account with Google Sheets access. |



### Creating a custom dashboard widget

Note: Currently bmoney only supports creating custom metric type dashboard widgets

There are two steps to create a custom dashboard widget:
1) Create a python function that generates the data for your custom widget
    a) Your function must return a dict object with the keys `title`,`value` and optionally `delta`.
2) Update your config.json with a new entry to the CUSTOM_WIDGETS list

For example we could create a script `my_new_metric.py` in our project folder with the following function:

```python
from bmoney.utils.data import load_master_transaction_df
import pandas as pd

def get_category_cost_data(category):
    df = load_master_transaction_df()
    total_amount = round(df[df["Category"]==category]["Amount"].sum(),2)
    
    data = {"title": f"All time {category} cost",
            "value": total_amount}
    return data
```

And in your `config.json` file:
```json
"CUSTOM_WIDGETS":[{
        "name": "Total Pet Cost",
        "type": "metric",
        "script_path": "./my_new_metric.py",
        "function_name":"get_category_cost_data",
        "args": ["Pets"],
        "kwargs": {}
    }]
```

Now when you run `bmoney launch` you'll see your new metric in your Mission Control (front page).