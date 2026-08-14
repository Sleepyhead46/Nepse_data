import re
from pathlib import Path
import pandas as pd

from utils.status import getStatus
from utils.session import make_session, fetch_today_share_prices

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


def clean_number(val, default=0.0):
    """Safely converts string or numeric values with commas/spaces to float."""
    if val is None or pd.isna(val):
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(",", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def main():
    file_dir = (Path(__file__).resolve().parent.parent / "data" / "company-wise").resolve()
    file_dir.mkdir(parents=True, exist_ok=True)

    session = make_session()
    print("Fetching today's share prices from ShareSansar...")
    try:
        today, data_table = fetch_today_share_prices(session)
    except Exception as exc:
        print(f"Error fetching daily prices: {exc}")
        return

    if not today:
        print("Warning: Could not determine market date from response.")
        return

    print(f"Market Date: {today}")

    if "Symbol" not in data_table.columns:
        print("Error: 'Symbol' column not found in table.")
        return

    symbols = data_table["Symbol"].dropna().unique()
    total_symbols = len(symbols)
    updated_count = 0
    new_count = 0

    print(f"Processing daily data for {total_symbols} symbols (updating to {today})...")

    for raw_symbol in symbols:
        raw_symbol_str = str(raw_symbol).strip()
        matching = data_table.loc[data_table["Symbol"] == raw_symbol]
        if matching.empty:
            continue

        symbol = re.sub(r"[^\w\-]", "_", raw_symbol_str)
        out_file = file_dir / f"{symbol}.csv"

        row = matching.iloc[0]
        open_val = clean_number(row.get("Open", 0.0))
        high_val = clean_number(row.get("High", 0.0))
        low_val = clean_number(row.get("Low", 0.0))
        close_val = clean_number(row.get("Close", 0.0))
        per_change = clean_number(row.get("Diff %", row.get("Diff", 0.0)))
        vol = clean_number(row.get("Vol", row.get("Traded Quantity", 0.0)))
        turnover = clean_number(row.get("Turnover", row.get("Traded Amount", 0.0)))
        status = getStatus(open_val, close_val)

        data_row = [
            [
                today,
                open_val,
                high_val,
                low_val,
                close_val,
                per_change,
                vol,
                turnover,
                status,
            ]
        ]
        new_df = pd.DataFrame(data_row, columns=DAILY_COLUMNS)

        if out_file.exists() and out_file.stat().st_size > 0:
            try:
                existing_df = pd.read_csv(out_file)
                # Filter out today's previous row if re-running intra-day
                existing_df = existing_df[existing_df["published_date"].astype(str).str.strip() != today]
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=["published_date"], keep="last")
                combined_df = combined_df.sort_values(by="published_date").reset_index(drop=True)
                combined_df.to_csv(out_file, index=False)
                updated_count += 1
            except Exception:
                new_df.to_csv(out_file, index=False)
                updated_count += 1
        else:
            new_df.to_csv(out_file, index=False)
            new_count += 1

    print(
        f"Daily scrape complete. Updated/Appended: {updated_count}, New companies created: {new_count} (Market Date: {today})."
    )


if __name__ == "__main__":
    main()
