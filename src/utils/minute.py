import pandas as pd
from utils.status import getStatus

MINUTE_COLUMNS = [
    "published_date",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "per_change",
    "traded_quantity",
    "traded_amount",
    "status",
]


def format_minute_row(date_str, time_str, row_data):
    """Formats raw scraped row into a per-minute record list.

    row_data expected keys/Series: Open, High, Low, Close, Diff %, Vol (or
    Traded Quantity), Turnover (or Traded Amount).
    """
    open_p = float(row_data.get("Open", 0.0))
    high_p = float(row_data.get("High", 0.0))
    low_p = float(row_data.get("Low", 0.0))
    close_p = float(row_data.get("Close", 0.0))
    per_change = float(row_data.get("Diff %", 0.0))

    # Handles both 'Vol' / 'Traded Quantity' and 'Turnover' / 'Traded Amount' column names
    vol = float(row_data.get("Vol", row_data.get("Traded Quantity", 0.0)))
    turnover = float(row_data.get("Turnover", row_data.get("Traded Amount", 0.0)))
    status = getStatus(open_p, close_p)

    timestamp = f"{date_str} {time_str}"
    return [
        date_str,
        timestamp,
        open_p,
        high_p,
        low_p,
        close_p,
        per_change,
        vol,
        turnover,
        status,
    ]


def minute_records_to_dataframe(records):
    """Converts a list of formatted per-minute records to a pandas DataFrame."""
    return pd.DataFrame(records, columns=MINUTE_COLUMNS)
