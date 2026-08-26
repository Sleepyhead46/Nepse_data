import sys
import time
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

    stages = [
        ("Discovering New Listed Companies", [run_discover]),
        ("Updating Daily Close Data (Last Date to Current)", [run_daily]),
        (
            "Updating Hourly Data (Live Snapshot & Incremental Backfill)",
            [run_hourly, run_backfill_hourly],
        ),
        (
            "Updating Minute Data (Live Snapshot & Incremental Backfill)",
            [run_minute, run_backfill_minute],
        ),
    ]

    overall_start = time.perf_counter()

    for stage_no, (label, runners) in enumerate(stages, 1):
        print(f"\n[{stage_no}/{len(stages)}] {label}...")
        stage_start = time.perf_counter()
        for runner in runners:
            try:
                runner()
            except Exception as exc:
                print(f"{label} error: {exc}")
        print(
            f"\n[{stage_no}/{len(stages)}] {label} finished "
            f"in {time.perf_counter() - stage_start:.1f}s."
        )

    print("\n==================================================")
    print(
        f"All NEPSE Datasets Updated to Current! "
        f"(total {time.perf_counter() - overall_start:.1f}s)"
    )
    print("==================================================")


if __name__ == "__main__":
    main()
