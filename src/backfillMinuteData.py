import argparse
import os
import re
from pathlib import Path
import pandas as pd
from utils.minute import MINUTE_COLUMNS
from utils.status import getStatus

DAILY_DIR = (Path(__file__).resolve().parent.parent / "data" / "company-wise").resolve()
MINUTE_DIR = (Path(__file__).resolve().parent.parent / "data" / "company-wise-minute").resolve()


def generate_trading_minute_timestamps(step_minutes=1):
    """Generates standard NEPSE trading day minute timestamps between 11:00:00 and 15:00:00."""
    timestamps = []
    # 11:00 to 15:00 is 240 minutes
    total_minutes = 240
    for offset in range(0, total_minutes + 1, step_minutes):
        hours = 11 + (offset // 60)
        mins = offset % 60
        timestamps.append(f"{hours:02d}:{mins:02d}:00")
    return timestamps


def interpolate_minute_day(row, trading_intervals):
    """Interpolates a daily OHLCV record into minute trading records."""
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

    num_intervals = len(trading_intervals)
    vol_interval = round(vol / num_intervals, 2) if vol else 0.0
    turnover_interval = round(turnover / num_intervals, 2) if turnover else 0.0

    minute_rows = []
    prev_close = o

    for i, t_str in enumerate(trading_intervals):
        timestamp = f"{date_str} {t_str}"
        frac = i / max(1, (num_intervals - 1))
        next_frac = (i + 1) / max(1, (num_intervals - 1)) if i + 1 < num_intervals else 1.0

        m_open = round(o + (c - o) * frac, 2)
        m_close = round(o + (c - o) * next_frac, 2)

        # Distribute intra-day high and low boundaries across trading intervals
        if i == 0:
            m_high = max(m_open, m_close, round(o + (h - o) * 0.3, 2))
            m_low = min(m_open, m_close, round(o - (o - l) * 0.3, 2))
        elif i == num_intervals // 2:
            m_high = max(m_open, m_close, h)
            m_low = min(m_open, m_close, l)
        elif i == num_intervals - 1:
            m_high = max(m_open, m_close, h)
            m_low = min(m_open, m_close, l)
        else:
            m_high = max(m_open, m_close)
            m_low = min(m_open, m_close)

        per_change = round(((m_close - prev_close) / prev_close * 100), 2) if prev_close else 0.0
        status = getStatus(m_open, m_close)

        minute_rows.append(
            [
                date_str,
                timestamp,
                m_open,
                m_high,
                m_low,
                m_close,
                per_change,
                vol_interval,
                turnover_interval,
                status,
            ]
        )
        prev_close = m_close

    return minute_rows


def _last_timestamp_from_tail(file_path, nbytes=65536):
    """Reads only the trailing bytes of the CSV and returns the last row's
    timestamp ('YYYY-MM-DD HH:MM:SS'), '' when the file holds no data rows yet
    (header only), or None when the tail cannot be trusted (crash-truncated
    final line, corrupt content). Minute files are written chronologically
    sorted, so the last line always carries the newest record."""
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


def _interpolate_days(daily_to_process, trading_intervals):
    """Interpolates each selected daily row into per-minute records."""
    all_minute_records = []
    for _, row in daily_to_process.iterrows():
        all_minute_records.extend(interpolate_minute_day(row, trading_intervals))
    return all_minute_records


def _full_merge_backfill(file_path, daily_df, trading_intervals, limit_days, out_file, clean_symbol):
    """Whole-file strategy: load the entire minute CSV, merge, de-duplicate and
    rewrite. Only used when the incremental tail read is unreliable."""
    existing_minute_df = None
    last_minute_date = None
    last_minute_timestamp = None

    try:
        existing_minute_df = pd.read_csv(out_file)
        if "published_date" in existing_minute_df.columns and not existing_minute_df.empty:
            existing_minute_dates = set(
                existing_minute_df["published_date"].dropna().astype(str).str.strip().values
            )
            last_minute_date = str(existing_minute_df["published_date"].dropna().max()).strip()
            if "timestamp" in existing_minute_df.columns:
                last_minute_timestamp = str(
                    existing_minute_df["timestamp"].dropna().astype(str).str.strip().max()
                ).strip()
            else:
                last_minute_timestamp = last_minute_date
    except Exception:
        existing_minute_df = None

    if last_minute_date:
        dates = daily_df["published_date"].astype(str).str.strip()
        daily_to_process = daily_df[
            (dates > last_minute_date) | (~dates.isin(existing_minute_dates))
        ]
    else:
        daily_to_process = daily_df

    if limit_days and len(daily_to_process) > limit_days:
        daily_to_process = daily_to_process.tail(limit_days)

    if daily_to_process.empty:
        held_rows = len(existing_minute_df) if existing_minute_df is not None else 0
        return (
            0,
            "up_to_date",
            f"{clean_symbol} already holds every available record "
            f"({held_rows} rows up to {last_minute_timestamp}).",
        )

    all_minute_records = _interpolate_days(daily_to_process, trading_intervals)

    if not all_minute_records:
        return (
            0,
            "no_valid_data",
            f"{clean_symbol}: daily rows present but none produced valid minute bars.",
        )

    new_minute_df = pd.DataFrame(all_minute_records, columns=MINUTE_COLUMNS)

    if existing_minute_df is not None and not existing_minute_df.empty:
        combined_df = pd.concat([existing_minute_df, new_minute_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=["timestamp"], keep="last")
        combined_df = combined_df.sort_values(by="timestamp").reset_index(drop=True)
        combined_df.to_csv(out_file, index=False)
        return (
            len(new_minute_df),
            "updated",
            f"{clean_symbol} appended {len(new_minute_df)} new rows "
            f"(total {len(combined_df)}) -> {out_file.name}",
        )
    else:
        new_minute_df = new_minute_df.sort_values(by="timestamp").reset_index(drop=True)
        new_minute_df.to_csv(out_file, index=False)
        return (
            len(new_minute_df),
            "created",
            f"{clean_symbol} created new file with {len(new_minute_df)} rows -> {out_file.name}",
        )


def process_company_minute_backfill(file_path, trading_intervals, limit_days=None):
    """Processes a single company's daily CSV incrementally to backfill minute data
    from the last recorded date/time up to current.

    Fast incremental path: finds the newest recorded timestamp from the file
    tail alone and APPENDS freshly interpolated days - the multi-MB minute
    files are never fully loaded or rewritten (fully reloading + rewriting all
    companies' files used to cost ~10 GB of disk IO per run). Falls back to
    _full_merge_backfill only when the tail cannot be trusted.

    ponytail: days older than the file's last date are assumed already present
    (minute data is only ever generated from these same daily files, and new
    dates only arrive at the end). Mid-history gap healing is therefore not
    automatic anymore; upgrade path is a small sidecar per-symbol date index.

    Returns (new-row-count, status, message) where status is one of
    created | updated | up_to_date | empty | no_valid_data."""
    symbol = file_path.stem
    clean_symbol = re.sub(r"[^\w\-]", "_", symbol)

    daily_df = pd.read_csv(file_path)
    if daily_df.empty or "published_date" not in daily_df.columns:
        return 0, "empty", f"{symbol}: no usable daily data."

    out_file = MINUTE_DIR / f"{clean_symbol}.csv"
    has_data = out_file.exists() and out_file.stat().st_size > 0

    if has_data:
        last_timestamp = _last_timestamp_from_tail(out_file)
        if last_timestamp is None:  # untrusted tail -> safe full merge
            return _full_merge_backfill(
                file_path, daily_df, trading_intervals, limit_days, out_file, clean_symbol
            )
        last_minute_date = last_timestamp[:10] if last_timestamp else None
        if last_minute_date:
            dates = daily_df["published_date"].astype(str).str.strip()
            daily_to_process = daily_df[dates > last_minute_date]
        else:  # header-only file: everything still needs backfilling
            daily_to_process = daily_df
    else:
        daily_to_process = daily_df

    if limit_days and len(daily_to_process) > limit_days:
        daily_to_process = daily_to_process.tail(limit_days)

    if daily_to_process.empty:
        return (
            0,
            "up_to_date",
            f"{clean_symbol} already holds every available record (up to {last_timestamp}).",
        )

    all_minute_records = _interpolate_days(daily_to_process, trading_intervals)

    if not all_minute_records:
        return (
            0,
            "no_valid_data",
            f"{clean_symbol}: daily rows present but none produced valid minute bars.",
        )

    new_minute_df = pd.DataFrame(all_minute_records, columns=MINUTE_COLUMNS)
    new_minute_df = new_minute_df.sort_values(by="timestamp").reset_index(drop=True)

    if has_data:  # chronological append - never rewrite the existing file
        new_minute_df.to_csv(out_file, mode="a", header=False, index=False)
        return (
            len(new_minute_df),
            "updated",
            f"{clean_symbol} appended {len(new_minute_df)} new rows "
            f"(up to {new_minute_df['timestamp'].iloc[-1]}) -> {out_file.name}",
        )

    new_minute_df.to_csv(out_file, index=False)
    return (
        len(new_minute_df),
        "created",
        f"{clean_symbol} created new file with {len(new_minute_df)} rows -> {out_file.name}",
    )


def main():
    parser = argparse.ArgumentParser(description="NEPSE Minute-Wise Data Backfill Utility")
    parser.add_argument(
        "--step",
        type=int,
        default=1,
        help="Intraday step in minutes (default: 1 min)",
    )
    parser.add_argument(
        "--limit-days",
        type=int,
        default=None,
        help="Limit number of most recent daily rows to backfill per company",
    )
    args = parser.parse_args()

    MINUTE_DIR.mkdir(parents=True, exist_ok=True)
    trading_intervals = generate_trading_minute_timestamps(step_minutes=args.step)

    daily_files = list(DAILY_DIR.glob("*.csv"))
    total_files = len(daily_files)
    print(f"Starting incremental minute backfill ({args.step}-min resolution from last date to current) for {total_files} companies...")

    updated_companies = 0
    up_to_date_companies = 0
    created_companies = 0
    failed_companies = 0
    total_new_records = 0

    for done, file_path in enumerate(daily_files, start=1):
        try:
            count, status, message = process_company_minute_backfill(
                file_path, trading_intervals, limit_days=args.limit_days
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
        f"\nMinute backfill complete! "
        f"Created: {created_companies}, Updated: {updated_companies}, "
        f"Already up-to-date: {up_to_date_companies}, Failed: {failed_companies}. "
        f"Total new minute records generated: {total_new_records}."
    )


if __name__ == "__main__":
    main()
