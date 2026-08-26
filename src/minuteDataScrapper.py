import argparse
import datetime
import os
import re
import time
from pathlib import Path
import pandas as pd

from utils.minute import MINUTE_COLUMNS, format_minute_row, minute_records_to_dataframe
from utils.session import make_session, fetch_today_share_prices

OUT_DIR = (Path(__file__).resolve().parent.parent / "data" / "company-wise-minute").resolve()


def check_timestamp_exists(file_path, target_timestamp):
    """Fast check whether target_timestamp already exists in the minute CSV."""
    if not file_path.exists() or file_path.stat().st_size == 0:
        return False

    target_str = str(target_timestamp).strip()
    try:
        # Fast tail check: read last 4KB to see if recent timestamp is present
        with open(file_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            seek_pos = max(0, size - 4096)
            f.seek(seek_pos)
            tail_content = f.read().decode("utf-8", errors="ignore")
            if target_str in tail_content:
                return True

        # Fallback to checking full timestamp column if not found in tail
        df = pd.read_csv(file_path, usecols=["timestamp"])
        timestamps = set(df["timestamp"].dropna().astype(str).str.strip().values)
        return target_str in timestamps
    except Exception:
        try:
            df = pd.read_csv(file_path)
            if "timestamp" in df.columns:
                timestamps = set(df["timestamp"].dropna().astype(str).str.strip().values)
                return target_str in timestamps
        except Exception:
            return False
    return False


def scrape_minute_snapshot(session=None, time_str=None):
    """Captures a minute-level snapshot of share prices and appends to per-company CSV files."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if session is None:
        session = make_session()

    now = datetime.datetime.now()
    if time_str is None:
        time_str = now.strftime("%H:%M:00")

    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Fetching NEPSE minute snapshot ({time_str})...")

    try:
        today_date, data_table = fetch_today_share_prices(session)
    except Exception as exc:
        print(f"Error fetching share prices: {exc}")
        return

    if "Symbol" not in data_table.columns:
        print("Error: 'Symbol' column not found in price table.")
        return

    # One pass over unique symbols instead of a full-table .loc filter per symbol
    unique_rows = data_table.dropna(subset=["Symbol"]).drop_duplicates(subset=["Symbol"], keep="first")
    updated_count = 0
    skipped_count = 0
    new_count = 0

    for row_data in unique_rows.to_dict("records"):
        raw_symbol_str = str(row_data["Symbol"]).strip()
        symbol = re.sub(r"[^\w\-]", "_", raw_symbol_str)
        formatted_row = format_minute_row(today_date, time_str, row_data)
        current_timestamp = formatted_row[1]

        out_file = OUT_DIR / f"{symbol}.csv"

        # Skip if this minute timestamp is already recorded
        if check_timestamp_exists(out_file, current_timestamp):
            skipped_count += 1
            continue

        new_df = minute_records_to_dataframe([formatted_row])
        if out_file.exists() and out_file.stat().st_size > 0:
            new_df.to_csv(out_file, mode="a", header=False, index=False)
            updated_count += 1
        else:
            new_df.to_csv(out_file, index=False)
            new_count += 1

    print(
        f"Minute snapshot complete ({today_date} {time_str}). "
        f"Updated: {updated_count}, New files: {new_count}, Skipped (already fetched): {skipped_count}."
    )


def main():
    parser = argparse.ArgumentParser(description="NEPSE Minute-Wise Data Scraper")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously every interval during market trading hours",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Interval in seconds for continuous loop (default: 60)",
    )
    args = parser.parse_args()

    session = make_session()

    if args.loop:
        print(f"Starting continuous minute collection (interval: {args.interval}s)...")
        while True:
            scrape_minute_snapshot(session)
            time.sleep(args.interval)
    else:
        scrape_minute_snapshot(session)


if __name__ == "__main__":
    main()
