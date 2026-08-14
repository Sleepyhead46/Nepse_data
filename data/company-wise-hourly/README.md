# Company-Wise Hourly Stock Data

This directory contains hourly historical stock price records for individual NEPSE-listed companies.

Each CSV file is named `{SYMBOL}.csv` (e.g. `ADBL.csv`, `NABIL.csv`) and contains the following columns:
- `published_date`: Date in `YYYY-MM-DD` format
- `timestamp`: Date and hour timestamp in `YYYY-MM-DD HH:00:00` format
- `open`: Opening price of the hourly period
- `high`: Highest price of the hourly period
- `low`: Lowest price of the hourly period
- `close`: Closing price of the hourly period
- `per_change`: Percentage change from previous period
- `traded_quantity`: Total volume traded
- `traded_amount`: Total turnover amount traded
- `status`: Status indicator (1 for Gain, -1 for Loss, 0 for Neutral)
