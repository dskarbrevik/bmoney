# Budget Money

Budget Money (bmoney) is a budgeting tool that builds on top of Rocket Money transaction exports.

---

Rocket Money allows users to export their financial transactions to a CSV file. Rocket Money (through their partnered service Plaid) provide transactions up to two years ago.

Budget Money (this tool) provides an easy way to  takes in one or more of these CSVs in order to produce statistics and visualizations to help a user better understand their spending and achieve their budgeting goals.

- Merge multiple Rocket Money CSV export files into one highly portable JSONL file
- Display and easily edit your data
- Extends Rocket Money metadata:
    - Custom categories
    - "Shared expenses" to make it easier to separate expenses with partners
- Metrics and visualization dashboard to see category spending habit in more detail
- Export category spend data to Google Sheets 

# Installation

`pip install bmoney`

Once `bmoney` is installed in your environment, you can navigate to a directory where you want to store your transaction data files. Make sure you have a Rocket Money transaction export CSV file in that folder before using the bmoney cmds below.

## Basic usage

`bmoney init`

You should see a a config.json and jsonl transaction file in your folder now.

`bmoney launch` to see the budget money dashboard

### Explanation of config.json file

On `bmoney init` the `config.json` file comes pre-populated with many default values. The config file is a recent (v0.2.x) introduction and some variables may cause issues if they are edited in certain ways.

Below is an explanation of variables in `config.json` along with a declaration of whether I'd recommend manipulating this variable currently. Obviously all variables should be editable but this is just a toy personal project after all :)

| name | type | description | notes |
| --- | --- | --- | --- |
| MASTER_DF_FILENAME | `str` | Filename for master jsonl transactions | |
| SHARED_EXPENSES | `list(str)` | CUSTOM_CAT vals that will have `SHARED==True` in master df| |
| CAT_MAP | `dict(str`) | Mapping Rocket Money categories to your own custom categories | There is an interplay between SHARED_EXPENSES and CAT_MAP. |
| DATA_VIEW_COLS | `list(str)` | The name of master df columns to show in the app's data editor tab | |
| GSHEETS_CONFIG | `dict(str)` | Vars important for using the Google Sheets integration | |
| BUDGET_MONEY_USER | `str` | Username, this is applied to create the Person col in the master df | This will be asked on `bmoney init` if not expressly provided to that command|