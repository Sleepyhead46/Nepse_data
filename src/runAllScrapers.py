import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from discoverCompanies import main as run_discover
from dailyDataScrapper import main as run_daily
from hourlyDataScrapper import main as run_hourly


def main():
    print("========================================")
    print("Starting NEPSE Data Scraper Suite")
    print("========================================\n")

    print("[1/3] Discovering New Listed Companies...")
    try:
        run_discover()
        print("Company discovery finished.")
    except Exception as exc:
        print(f"Company discovery error: {exc}")

    print("\n[2/3] Running Daily Scraper...")
    try:
        run_daily()
        print("Daily scraper finished.")
    except Exception as exc:
        print(f"Daily scraper error: {exc}")

    print("\n[3/3] Running Hourly Scraper...")
    try:
        run_hourly()
        print("Hourly scraper finished.")
    except Exception as exc:
        print(f"Hourly scraper error: {exc}")

    print("\n========================================")
    print("All NEPSE Data Scrapers Completed!")
    print("========================================")


if __name__ == "__main__":
    main()

