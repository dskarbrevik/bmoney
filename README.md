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