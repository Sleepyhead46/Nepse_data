import argparse
import re
from pathlib import Path
import pandas as pd
from utils.hourly import HOURLY_COLUMNS
from utils.status import getStatus

DAILY_DIR = (Path(__file__).resolve().parent.parent / "data" / "company-wise").resolve()
HOURLY_DIR = (Path(__file__).resolve().parent.parent / "data" / "company-wise-hourly").resolve()

TRADING_HOURS = ["11:00:00", "12:00:00", "13:00:00", "14:00:00", "15:00:00"]


def interpolate_hourly_day(row):
    """Interpolates a daily OHLCV record into 5 hourly trading records."""
    date_str = str(row.get("published_date", "")).strip()
    if not date_str or date_str == "nan":
        return []

    try:
        o = float(row.get("open", 0.0))
        h = float(row.get("high", o))
        l = float(row.get("low", o))
        c = float(row.get("close", o))
        vol = float(row.get("traded_quantity", 0.0))
        turnover = float(row.get("traded_amount", 0.0))
    except (ValueError, TypeError):
        return []

    if pd.isna(o) or pd.isna(c):
        return []

    if pd.isna(h):
        h = max(o, c)
    if pd.isna(l):
        l = min(o, c)

    vol_hourly = round(vol / len(TRADING_HOURS), 2) if vol else 0.0
    turnover_hourly = round(turnover / len(TRADING_HOURS), 2) if turnover else 0.0

    # Hourly price steps between open and close
    steps = [0.0, 0.25, 0.50, 0.75, 1.0]
    hourly_rows = []
    prev_close = o

    for i, t_str in enumerate(TRADING_HOURS):
        timestamp = f"{date_str} {t_str}"
        step = steps[i]
        next_step = steps[i + 1] if i + 1 < len(steps) else 1.0

        h_open = round(o + (c - o) * step, 2)
        h_close = round(o + (c - o) * next_step, 2)

        # Distribute intra-day high and low boundaries across trading hours
        if i == 0:
            h_high = max(h_open, h_close, round(o + (h - o) * 0.5, 2))
            h_low = min(h_open, h_close, round(o - (o - l) * 0.5, 2))
        elif i == len(TRADING_HOURS) - 1:
            h_high = max(h_open, h_close, h)
            h_low = min(h_open, h_close, l)
        else:
            h_high = max(h_open, h_close)
            h_low = min(h_open, h_close)

        per_change = round(((h_close - prev_close) / prev_close * 100), 2) if prev_close else 0.0
        status = getStatus(h_open, h_close)

        hourly_rows.append(
            [
                date_str,
                timestamp,
                h_open,
                h_high,
                h_low,
                h_close,
                per_change,
                vol_hourly,
                turnover_hourly,
                status,
            ]
        )
        prev_close = h_close

    return hourly_rows


def process_company_backfill(file_path, limit_days=None):
    """Processes a single company's daily CSV incrementally to backfill hourly data
    from the last hourly recorded date up to the current latest date.

    Returns (new-row-count, status, message) where status is one of
    created | updated | up_to_date | empty | no_valid_data."""
    symbol = file_path.stem
    clean_symbol = re.sub(r"[^\w\-]", "_", symbol)

    daily_df = pd.read_csv(file_path)
    if daily_df.empty or "published_date" not in daily_df.columns:
        return 0, "empty", f"{symbol}: no usable daily data."

    out_file = HOURLY_DIR / f"{clean_symbol}.csv"

    # Find the latest date already backfilled in hourly CSV
    last_hourly_date = None
    last_hourly_timestamp = None
    existing_hourly_dates = set()
    existing_hourly_df = None

    if out_file.exists() and out_file.stat().st_size > 0:
        try:
            existing_hourly_df = pd.read_csv(out_file)
            if "published_date" in existing_hourly_df.columns and not existing_hourly_df.empty:
                existing_hourly_dates = set(
                    existing_hourly_df["published_date"].dropna().astype(str).str.strip().values
                )
                last_hourly_date = str(existing_hourly_df["published_date"].dropna().max()).strip()
                if "timestamp" in existing_hourly_df.columns:
                    last_hourly_timestamp = str(
                        existing_hourly_df["timestamp"].dropna().astype(str).str.strip().max()
                    ).strip()
                else:
                    last_hourly_timestamp = last_hourly_date
        except Exception:
            existing_hourly_df = None

    if last_hourly_date:
        daily_to_process = daily_df[
            (daily_df["published_date"].astype(str).str.strip() > last_hourly_date)
            | (~daily_df["published_date"].astype(str).str.strip().isin(existing_hourly_dates))
        ]
    else:
        daily_to_process = daily_df

    if limit_days and len(daily_to_process) > limit_days:
        daily_to_process = daily_to_process.tail(limit_days)

    if daily_to_process.empty:
        held_rows = len(existing_hourly_df) if existing_hourly_df is not None else 0
        return (
            0,
            "up_to_date",
            f"{clean_symbol} already holds every available record "
            f"({held_rows} rows up to {last_hourly_timestamp}).",
        )

    all_hourly_records = []
    for _, row in daily_to_process.iterrows():
        records = interpolate_hourly_day(row)
        all_hourly_records.extend(records)

    if not all_hourly_records:
        return (
            0,
            "no_valid_data",
            f"{clean_symbol}: daily rows present but none produced valid hourly bars.",
        )

    new_hourly_df = pd.DataFrame(all_hourly_records, columns=HOURLY_COLUMNS)

    if existing_hourly_df is not None and not existing_hourly_df.empty:
        combined_df = pd.concat([existing_hourly_df, new_hourly_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=["timestamp"], keep="last")
        combined_df = combined_df.sort_values(by="timestamp").reset_index(drop=True)
        combined_df.to_csv(out_file, index=False)
        return (
            len(new_hourly_df),
            "updated",
            f"{clean_symbol} appended {len(new_hourly_df)} new rows "
            f"(total {len(combined_df)}) -> {out_file.name}",
        )
    else:
        new_hourly_df = new_hourly_df.sort_values(by="timestamp").reset_index(drop=True)
        new_hourly_df.to_csv(out_file, index=False)
        return (
            len(new_hourly_df),
            "created",
            f"{clean_symbol} created new file with {len(new_hourly_df)} rows -> {out_file.name}",
        )


def main():
    parser = argparse.ArgumentParser(description="NEPSE Hourly Data Incremental Backfill")
    parser.add_argument(
        "--limit-days",
        type=int,
        default=None,
        help="Limit number of most recent daily rows to backfill per company",
    )
    args = parser.parse_args()

    HOURLY_DIR.mkdir(parents=True, exist_ok=True)

    daily_files = list(DAILY_DIR.glob("*.csv"))
    total_files = len(daily_files)
    print(f"Starting incremental hourly backfill (from last date to current) for {total_files} companies...")

    updated_companies = 0
    up_to_date_companies = 0
    created_companies = 0
    failed_companies = 0
    total_new_records = 0

    for done, file_path in enumerate(daily_files, start=1):
        try:
            count, status, message = process_company_backfill(
                file_path, limit_days=args.limit_days
            )
        except Exception as exc:  # noqa: BLE001 - one bad file must not kill the run
            failed_companies += 1
            print(f"[{done}/{total_files}] {file_path.stem}: FAILED ({type(exc).__name__}): {exc}")
            continue

        if status == "updated":
            updated_companies += 1
            total_new_records += count
        elif status == "created":
            created_companies += 1
            total_new_records += count
        elif status == "up_to_date":
            up_to_date_companies += 1

        print(f"[{done}/{total_files}] {message}")

    print(
        f"\nHourly backfill complete! "
        f"Created: {created_companies}, Updated: {updated_companies}, "
        f"Already up-to-date: {up_to_date_companies}, Failed: {failed_companies}. "
        f"Total new hourly records generated: {total_new_records}."
    )


if __name__ == "__main__":
    main()
