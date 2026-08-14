import time
import requests
from pathlib import Path
import pandas as pd

from constants.companyIdMap import companyIdMap
from constants.url import historyUrl
from utils.session import make_session, prime_session, TIMEOUT
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


def fetch_history(session, token, company_id, existing_dates=None, size=PAGE_SIZE):
    """Fetch history rows for a company (newest-first). If existing_dates is provided,
    stops pagination early once already-recorded dates are encountered and returns
    only the un-fetched new records."""
    if existing_dates is None:
        first = _post(session, token, company_id, 0, 1)
        total = records_total(first)
        rows = []
        for start in page_starts(total, size):
            page = _post(session, token, company_id, start, size)
            records_total(page)  # guard against silent auth errors
            rows.extend(page.get("data", []))
        return rows

    # Incremental fetch mode
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
            if rec_date in existing_dates:
                reached_existing = True
            else:
                new_rows.append(rec)

        # Stop pagination if we reached records already present in local data
        if reached_existing or (start + size >= total) or len(page_records) < size:
            break

        start += size

    return new_rows


def collect_company(session, token, symbol, company_id, existing_dates=None):
    """Return (rows, token). rows is None on failure, [] if untraded or already up-to-date.
    Refreshes the CSRF token and retries on auth/HTTP/timeout errors."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fetch_history(session, token, company_id, existing_dates=existing_dates), token
        except (AuthError, requests.RequestException) as exc:
            print(f"  issue ({type(exc).__name__}): {exc}; refreshing token")
            time.sleep(2)
            try:
                token = prime_session(session)
            except requests.RequestException:
                pass
        except Exception as exc:  # noqa: BLE001 - keep the run alive
            print(f"  FAILED {symbol}: {exc}")
            return None, token
    return None, token


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = make_session()
    token = prime_session(session)

    seeded = updated = up_to_date = empty = failed = 0
    total_companies = len(companyIdMap)

    print(f"Starting NEPSE history scraper for {total_companies} companies (incremental mode)...")

    for idx, (symbol, company_id) in enumerate(companyIdMap.items(), 1):
        out_file = OUT_DIR / f"{symbol}.csv"
        existing_df = None
        existing_dates = None

        if out_file.exists() and out_file.stat().st_size > 0:
            try:
                existing_df = pd.read_csv(out_file)
                if "published_date" in existing_df.columns:
                    existing_dates = set(existing_df["published_date"].dropna().astype(str).str.strip().values)
            except Exception:
                existing_df = None
                existing_dates = None

        print(f"[{idx}/{total_companies}] Checking {symbol} (id={company_id})...")
        rows, token = collect_company(session, token, symbol, company_id, existing_dates=existing_dates)

        if rows is None:
            failed += 1
            continue

        if not rows:
            if existing_dates is not None:
                print(f"  {symbol} is already up to date ({len(existing_dates)} existing records).")
                up_to_date += 1
            else:
                print(f"  no records for {symbol} (untraded).")
                empty += 1
            continue

        new_df = records_to_dataframe(rows)

        if existing_df is not None and not existing_df.empty:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=["published_date"], keep="last")
            combined_df = combined_df.sort_values(by="published_date").reset_index(drop=True)
            combined_df.to_csv(out_file, index=False)
            print(f"  appended {len(new_df)} new rows (total {len(combined_df)}) -> {out_file.name}")
            updated += 1
        else:
            new_df.to_csv(out_file, index=False)
            print(f"  created new file with {len(new_df)} rows -> {out_file.name}")
            seeded += 1

    print(
        f"\nDone. seeded={seeded} updated={updated} up_to_date={up_to_date} empty={empty} failed={failed}"
    )


if __name__ == "__main__":
    main()
