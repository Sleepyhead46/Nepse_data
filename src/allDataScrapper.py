import random
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import pandas as pd

from constants.companyIdMap import companyIdMap
from constants.url import historyUrl
from utils.session import (
    TIMEOUT,
    WORKERS,
    get_thread_scraper,
    prime_session,
    set_thread_token,
)
from utils.params import build_history_payload
from utils.history import page_starts, records_to_dataframe, records_total, AuthError

OUT_DIR = (Path(__file__).resolve().parent.parent / "data" / "company-wise").resolve()
PAGE_SIZE = 50  # the API silently returns an empty result for length >= 100
DELAY = 0.3  # polite delay between requests (seconds)
MAX_ATTEMPTS = 4  # per company, refreshing the CSRF token between attempts


def _post(session, token, company_id, start, length):
    time.sleep(DELAY)
    payload = build_history_payload(start, length, company_id, token)
    resp = session.post(historyUrl, data=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_history(session, token, company_id, max_existing_date=None, existing_dates=None, size=PAGE_SIZE):
    """Fetch history rows for a company (newest-first). If max_existing_date is provided,
    stops pagination early as soon as records with date <= max_existing_date are encountered,
    returning only the newer un-fetched records from last date to current."""
    if not existing_dates and not max_existing_date:
        first = _post(session, token, company_id, 0, 1)
        total = records_total(first)
        rows = []
        for start in page_starts(total, size):
            page = _post(session, token, company_id, start, size)
            records_total(page)  # guard against silent auth errors
            rows.extend(page.get("data", []))
        return rows

    # Incremental fetch mode from last date to current
    new_rows = []
    start = 0
    while True:
        page = _post(session, token, company_id, start, size)
        total = records_total(page)
        page_records = page.get("data", [])
        if not page_records:
            break

        reached_existing = False
        for rec in page_records:
            rec_date = str(rec.get("published_date", "")).strip()
            if not rec_date:
                continue

            # If we encounter an existing date or date older than max_existing_date, stop
            if (max_existing_date and rec_date <= max_existing_date) or (existing_dates and rec_date in existing_dates):
                reached_existing = True
            else:
                new_rows.append(rec)

        # Stop pagination if we reached records already present in local data
        if reached_existing or (start + size >= total) or len(page_records) < size:
            break

        start += size

    return new_rows


def collect_company(symbol, company_id, max_existing_date=None, existing_dates=None):
    """Return rows for one company: None on failure, [] if untraded or already
    up-to-date. Uses this thread's own session/token; refreshes the CSRF token
    and retries on auth/HTTP/timeout errors (jittered so parallel workers don't
    retry in lockstep)."""
    session, token = get_thread_scraper()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fetch_history(
                session,
                token,
                company_id,
                max_existing_date=max_existing_date,
                existing_dates=existing_dates,
            )
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
    """Worker: fetches any missing history for one company and writes its CSV.
    Returns (status, message)."""
    out_file = OUT_DIR / f"{symbol}.csv"
    existing_df = None
    existing_dates = None
    max_existing_date = None

    if out_file.exists() and out_file.stat().st_size > 0:
        try:
            existing_df = pd.read_csv(out_file)
            if "published_date" in existing_df.columns and not existing_df.empty:
                existing_dates = set(existing_df["published_date"].dropna().astype(str).str.strip().values)
                max_existing_date = str(existing_df["published_date"].dropna().max()).strip()
        except Exception:
            existing_df = None
            existing_dates = None
            max_existing_date = None

    rows = collect_company(
        symbol,
        company_id,
        max_existing_date=max_existing_date,
        existing_dates=existing_dates,
    )

    if rows is None:
        return "failed", f"{symbol}: failed after {MAX_ATTEMPTS} attempts"

    if not rows:
        if existing_dates is not None:
            return (
                "up_to_date",
                f"{symbol} is already up to date ({len(existing_dates)} records, up to {max_existing_date}).",
            )
        return "empty", f"{symbol}: no records (untraded)."

    new_df = records_to_dataframe(rows)

    if existing_df is not None and not existing_df.empty:
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=["published_date"], keep="last")
        combined_df = combined_df.sort_values(by="published_date").reset_index(drop=True)
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

    total_companies = len(companyIdMap)

    print(
        f"Starting NEPSE history scraper for {total_companies} companies "
        f"(incremental mode: last date to current) using {WORKERS} parallel workers..."
    )

    counters = {"seeded": 0, "updated": 0, "up_to_date": 0, "empty": 0, "failed": 0}
    started = time.perf_counter()
    done = 0

    with ThreadPoolExecutor(max_workers=min(WORKERS, total_companies)) as pool:
        futures = [
            pool.submit(process_company, symbol, company_id)
            for symbol, company_id in companyIdMap.items()
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
        f"\nDone in {elapsed:.1f}s. seeded={counters['seeded']} updated={counters['updated']} "
        f"up_to_date={counters['up_to_date']} empty={counters['empty']} failed={counters['failed']}"
    )


if __name__ == "__main__":
    main()
