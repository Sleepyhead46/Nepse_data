import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from discoverCompanies import main as run_discover
from dailyDataScrapper import main as run_daily
from hourlyDataScrapper import main as run_hourly
from minuteDataScrapper import main as run_minute
from backfillHourlyData import main as run_backfill_hourly
from backfillMinuteData import main as run_backfill_minute


def main():
    print("==================================================")
    print("Starting NEPSE Incremental Update Suite")
    print("==================================================\n")

    print("[1/5] Discovering New Listed Companies...")
    try:
        run_discover()
        print("Company discovery finished.")
    except Exception as exc:
        print(f"Company discovery error: {exc}")

    print("\n[2/5] Updating Daily Close Data (Last Date to Current)...")
    try:
        run_daily()
        print("Daily scraper finished.")
    except Exception as exc:
        print(f"Daily scraper error: {exc}")

    print("\n[3/5] Updating Hourly Data (Live Snapshot & Incremental Backfill)...")
    try:
        run_hourly()
        run_backfill_hourly()
        print("Hourly update finished.")
    except Exception as exc:
        print(f"Hourly update error: {exc}")

    print("\n[4/5] Updating Minute Data (Live Snapshot & Incremental Backfill)...")
    try:
        run_minute()
        run_backfill_minute()
        print("Minute update finished.")
    except Exception as exc:
        print(f"Minute update error: {exc}")

    print("\n==================================================")
    print("All NEPSE Datasets Updated to Current!")
    print("==================================================")


if __name__ == "__main__":
    main()
