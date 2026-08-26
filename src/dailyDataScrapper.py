"""Daily OHLCV dataset updater backed by ShareSansar's company price-history API.

Instead of capturing a single live-snapshot row stamped with today's date,
every run queries the price-history endpoint for each company and merges ALL
published records into ``data/company-wise/<SYMBOL>.csv``. Trading days missed
by earlier runs self-heal on the next run, and newly listed companies get
their complete history seeded automatically.
"""

import importlib
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

import constants.companyIdMap as _company_id_map
from allDataScrapper import _post
from utils.history import AuthError, records_to_dataframe, records_total
from utils.session import (
    WORKERS,
    get_thread_scraper,
    prime_session,
    set_thread_token,
)

OUT_DIR = (Path(__file__).resolve().parent.parent / "data" / "company-wise").resolve()

PAGE_SIZE = 50     # the API silently returns an empty result for length >= 100
DELAY = 0.3        # polite delay between paged requests (seconds), applied in _post
MAX_ATTEMPTS = 4   # per company, refreshing the CSRF token between attempts

DAILY_COLUMNS = [
    "published_date",
    "open",
    "high",
    "low",
    "close",
    "per_change",
    "traded_quantity",
    "traded_amount",
    "status",
]


def load_company_map():
    """Returns the freshest symbol -> company-id mapping.

    discoverCompanies.py may have rewritten constants/companyIdMap.py earlier
    in the same pipeline run, so the module is re-loaded instead of trusting
    the copy that was imported at startup."""
    try:
        importlib.reload(_company_id_map)
    except Exception:  # noqa: BLE001 - fall back to the stale in-memory map
        pass
    return _company_id_map.companyIdMap


def read_existing_daily(file_path):
    """Loads an existing daily CSV.

    Returns (dataframe|None, existing-date-set|None, max-existing-date|None).
    None values mean the company has no usable local data yet and must be
    seeded with its complete published history."""
    if not file_path.exists() or file_path.stat().st_size == 0:
        return None, None, None
    try:
        df = pd.read_csv(file_path)
        if "published_date" not in df.columns or df.empty:
            return None, None, None
        dates = df["published_date"].dropna().astype(str).str.strip()
        return df, set(dates.values), str(dates.max()).strip()
    except Exception:
        return None, None, None


def merge_daily_records(existing_df, new_df):
    """Merges freshly fetched rows into the local dataset (newest wins)."""
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=["published_date"], keep="last")
    return combined_df.sort_values(by="published_date").reset_index(drop=True)


def fetch_missing(session, token, company_id, existing_dates, size=PAGE_SIZE):
    """Pages through the newest-first price history and returns every record
    whose published_date is not already stored locally.

    Unlike a plain "everything newer than the last local date" fetch, this also
    heals gaps in the middle of the local history (e.g. days missed by earlier
    runs). Pagination stops as soon as a whole page is already known - records
    only get older on subsequent pages - so an up-to-date company costs exactly
    one request."""
    collected = []
    start = 0
    while True:
        page = _post(session, token, company_id, start, size)
        total = records_total(page)
        records = page.get("data", [])
        if not records:
            break

        unknown_on_page = 0
        for rec in records:
            rec_date = str(rec.get("published_date", "")).strip()
            if not rec_date:
                continue
            if existing_dates is None or rec_date not in existing_dates:
                collected.append(rec)
                unknown_on_page += 1

        # Last page reached, or everything from here on is older & already stored.
        if (start + size >= total) or len(records) < size or unknown_on_page == 0:
            break
        start += size

    return collected


def sync_company(symbol, company_id, existing_dates):
    """Return rows for one company: None on failure, [] if nothing is missing.
    Uses this thread's own session/token. Refreshes the CSRF token and retries
    on auth/HTTP/timeout errors (jittered so parallel workers don't retry in
    lockstep)."""
    session, token = get_thread_scraper()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fetch_missing(session, token, company_id, existing_dates)
        except (AuthError, requests.RequestException) as exc:
            print(f"  {symbol} issue ({type(exc).__name__}): {exc}; refreshing token")
            time.sleep(2 + random.random())
            try:
                set_thread_token(prime_session(session))
            except requests.RequestException:
                pass
            session, token = get_thread_scraper()
        except Exception as exc:  # noqa: BLE001 - keep the run alive
            print(f"  FAILED {symbol}: {exc}")
            return None
    return None


def process_company(symbol, company_id):
    """Worker: syncs a single company and writes its CSV.

    Returns (status, message) where status is one of
    seeded | updated | up_to_date | empty | failed."""
    out_file = OUT_DIR / f"{symbol}.csv"
    existing_df, existing_dates, max_existing_date = read_existing_daily(out_file)

    rows = sync_company(symbol, company_id, existing_dates)

    if rows is None:
        return "failed", f"{symbol}: failed after {MAX_ATTEMPTS} attempts"

    if not rows:
        if existing_dates is not None:
            return (
                "up_to_date",
                f"{symbol} already holds every available record "
                f"({len(existing_dates)} rows up to {max_existing_date}).",
            )
        return "empty", f"{symbol}: no records (untraded or unknown id)."

    new_df = records_to_dataframe(rows)

    if existing_df is not None:
        combined_df = merge_daily_records(existing_df, new_df)
        combined_df.to_csv(out_file, index=False)
        return (
            "updated",
            f"{symbol} appended {len(new_df)} new rows (total {len(combined_df)}) -> {out_file.name}",
        )

    new_df = new_df.sort_values(by="published_date").reset_index(drop=True)
    new_df.to_csv(out_file, index=False)
    return "seeded", f"{symbol} created new file with {len(new_df)} rows -> {out_file.name}"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    company_map = load_company_map()
    total_companies = len(company_map)

    print(
        f"Starting NEPSE daily update via price-history API for "
        f"{total_companies} companies using {WORKERS} parallel workers..."
    )

    counters = {"seeded": 0, "updated": 0, "up_to_date": 0, "empty": 0, "failed": 0}
    started = time.perf_counter()
    done = 0

    with ThreadPoolExecutor(max_workers=min(WORKERS, total_companies)) as pool:
        futures = [
            pool.submit(process_company, symbol, company_id)
            for symbol, company_id in company_map.items()
        ]
        for future in as_completed(futures):
            done += 1
            try:
                status, message = future.result()
            except Exception as exc:  # noqa: BLE001 - a crashed worker must not kill the run
                counters["failed"] += 1
                print(f"[{done}/{total_companies}] worker crashed: {exc}")
                continue
            counters[status] += 1
            print(f"[{done}/{total_companies}] {message}")

    elapsed = time.perf_counter() - started
    print(
        f"\nDaily history sync complete in {elapsed:.1f}s! "
        f"Seeded: {counters['seeded']}, Updated: {counters['updated']}, "
        f"Already up-to-date: {counters['up_to_date']}, No records: {counters['empty']}, "
        f"Failed: {counters['failed']}."
    )


if __name__ == "__main__":
    main()
