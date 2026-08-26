import argparse
import datetime
import os
import re
import time
from pathlib import Path
import pandas as pd

from utils.hourly import HOURLY_COLUMNS, format_hourly_row, hourly_records_to_dataframe
from utils.session import make_session, fetch_today_share_prices

OUT_DIR = (Path(__file__).resolve().parent.parent / "data" / "company-wise-hourly").resolve()


def _last_line_timestamp(file_path, nbytes=65536):
    """Returns the last data row's timestamp ('YYYY-MM-DD HH:MM:SS'), '' when
    the file holds no data rows yet (header only), or None when the tail cannot
    be trusted (crash-truncated final line, corrupt content). Snapshot files
    are written chronologically, so the last line always carries the newest
    record."""
    if not file_path.exists() or file_path.stat().st_size == 0:
        return ""
    try:
        with open(file_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - nbytes))
            tail = f.read().decode("utf-8", errors="ignore")
        lines = [ln for ln in tail.splitlines() if ln.strip()]
        if len(lines) < 2:  # header only
            return ""
        parts = lines[-1].split(",")
        date_str, ts = parts[0].strip(), parts[1].strip()
        if len(ts) >= 19 and ts[4] == "-" and len(date_str) >= 10 and date_str[4] == "-":
            return ts
    except Exception:
        pass
    return None


def check_timestamp_exists(file_path, target_timestamp):
    """Fast chronological duplicate check against ONLY the last recorded
    timestamp.

    Snapshot rows are appended chronologically, so a target timestamp is
    already recorded iff it is <= the file's newest record. Reading one tail
    line is O(1); the previous full-column pandas fallback re-parsed every
    company's whole CSV on each snapshot, because a brand-new timestamp never
    matches the recent 4KB tail and therefore ALWAYS fell through to the slow
    full-file read. The full scan is kept only as a safety net for an
    untrusted (crash-truncated) final line."""
    verdict = _last_line_timestamp(file_path)
    if verdict is not None:
        target_str = str(target_timestamp).strip()
        return bool(verdict) and target_str <= verdict

    # Untrusted tail: fall back to the exact full-column scan.
    try:
        df = pd.read_csv(file_path, usecols=["timestamp"])
        timestamps = set(df["timestamp"].dropna().astype(str).str.strip().values)
        return str(target_timestamp).strip() in timestamps
    except Exception:
        return False


def scrape_hourly_snapshot(session=None, hour_str=None):
    """Captures an hourly snapshot of share prices and appends to per-company CSV files."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if session is None:
        session = make_session()

    now = datetime.datetime.now()
    if hour_str is None:
        hour_str = now.strftime("%H:00:00")

    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Fetching NEPSE hourly snapshot ({hour_str})...")

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
        formatted_row = format_hourly_row(today_date, hour_str, row_data)
        current_timestamp = formatted_row[1]

        out_file = OUT_DIR / f"{symbol}.csv"

        # Skip if this hourly timestamp is already recorded
        if check_timestamp_exists(out_file, current_timestamp):
            skipped_count += 1
            continue

        new_df = hourly_records_to_dataframe([formatted_row])
        if out_file.exists() and out_file.stat().st_size > 0:
            new_df.to_csv(out_file, mode="a", header=False, index=False)
            updated_count += 1
        else:
            new_df.to_csv(out_file, index=False)
            new_count += 1

    print(
        f"Hourly snapshot complete ({today_date} {hour_str}). "
        f"Updated: {updated_count}, New files: {new_count}, Skipped (already fetched): {skipped_count}."
    )


def main():
    parser = argparse.ArgumentParser(description="NEPSE Hourly Data Scraper")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously every hour during market trading hours",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Interval in seconds for continuous loop (default: 3600)",
    )
    args = parser.parse_args()

    session = make_session()

    if args.loop:
        print(f"Starting continuous hourly collection (interval: {args.interval}s)...")
        while True:
            scrape_hourly_snapshot(session)
            time.sleep(args.interval)
    else:
        scrape_hourly_snapshot(session)


if __name__ == "__main__":
    main()
