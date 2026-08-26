# 📈 NEPSE Stock Analytics

A self-updating stock market data pipeline and analytics dashboard for the **Nepal Stock Exchange (NEPSE)**. Historical daily, hourly, and minute-level OHLCV data is scraped automatically via GitHub Actions and visualized through a premium Streamlit dashboard with full technical analysis support.

---

## ✨ Features

### 📊 Dashboard (`src/app.py`)
- **Three granularities** — Daily, Hourly, and Minute resolution, selectable at runtime
- **Candlestick & Line charts** with Apple-inspired dark UI (glassmorphism, OLED black)
- **Timeframe presets** — 1M, 3M, 6M, YTD, 1Y, 3Y, 5Y, All Time, and Custom date range
- **Overlay indicators:**
  - SMA 20 / 50 / 200
  - EMA 20 / 50
  - Bollinger Bands (20, 2)
  - VWAP
  - Parabolic SAR
- **Oscillator subplots:**
  - Volume Histogram (color-coded bull/bear)
  - RSI (14)
  - MACD (12, 26, 9)
  - Stochastic Oscillator (14, 3)
  - ATR (14)
  - CCI (20)
  - Williams %R (14)
  - OBV (On-Balance Volume)
- **Hero stats card** — live price, change pill, period high/low, 52-week range, volume & turnover

### 🤖 Automated Data Pipeline
- **GitHub Actions** workflow runs daily at **4:30 PM NPT** (10:45 UTC)
- **Parallel scraping** — company history is fetched by a pool of concurrent
  workers (default `8`, tunable via the `SCRAPERS_WORKERS` environment
  variable); every worker keeps its own session & CSRF token
- Pipeline stages (in order):
  1. **Company Discovery** — detects newly listed companies
  2. **Daily Scraper** — syncs every company's complete price history from the ShareSansar price-history API (any days missed by previous runs self-heal on the next run)
  3. **Hourly Scraper** + **Hourly Backfill** — live snapshot + gap-filling
  4. **Minute Scraper** + **Minute Backfill** — live snapshot + gap-filling
- All data is committed directly back to the repository

---

## 📁 Project Structure

```
Nepse_data/
├── .github/
│   └── workflows/
│       └── schedule-updater.yml   # Daily automation (4:30 PM NPT)
├── data/
│   ├── company-wise/              # Daily OHLCV CSVs (one per ticker)
│   ├── company-wise-hourly/       # Hourly OHLCV CSVs
│   └── company-wise-minute/       # Minute-level OHLCV CSVs
├── src/
│   ├── app.py                     # Streamlit dashboard
│   ├── runAllScrapers.py          # Orchestrates all scraper stages
│   ├── discoverCompanies.py       # Discovers newly listed companies
│   ├── dailyDataScrapper.py       # Daily OHLCV scraper
│   ├── hourlyDataScrapper.py      # Hourly data scraper
│   ├── minuteDataScrapper.py      # Minute-level data scraper
│   ├── backfillHourlyData.py      # Hourly historical backfill
│   ├── backfillMinuteData.py      # Minute historical backfill
│   ├── allDataScrapper.py         # Full historical scraper (initial seed)
│   ├── config/                    # Configuration constants
│   ├── constants/                 # Shared constants & company-ID map
│   └── utils/                     # Shared utilities (session, history, status…)
├── requirements.txt               # Python dependencies (repo root)
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- `pip`

### 1. Clone the repository
```bash
git clone https://github.com/Sleepyhead46/Nepse_data.git
cd Nepse_data
```

### 2. Install dependencies
Dependencies live in the repo-root [`requirements.txt`](requirements.txt):
```bash
pip install -r requirements.txt
```

### 3. Seed historical data
The daily scraper seeds the **full published history** automatically the first
time it sees a company. For a manual full re-scrape you can still run:
```bash
python src/allDataScrapper.py
```

### 4. Run the dashboard
```bash
streamlit run src/app.py
```

### 5. Run all scrapers manually
```bash
python src/runAllScrapers.py
```

> Every script resolves its own directory via `sys.path`, so all commands above
> work directly from the repository root — no need to `cd src` first.

---

## 📦 Data Format

Each company CSV in `data/company-wise/` follows this schema:

| Column            | Type    | Description                         |
|-------------------|---------|-------------------------------------|
| `published_date`  | string  | Trading date (`YYYY-MM-DD`)         |
| `open`            | float   | Opening price (NPR)                 |
| `high`            | float   | Intraday high (NPR)                 |
| `low`             | float   | Intraday low (NPR)                  |
| `close`           | float   | Closing price (NPR)                 |
| `per_change`      | float   | Percentage change from previous day |
| `traded_quantity` | float   | Number of shares traded             |
| `traded_amount`   | float   | Total turnover (NPR)                |
| `status`          | string  | `Gain` / `Loss` / `Neutral`         |

Hourly and minute CSVs use a `timestamp` column (ISO 8601) instead of `published_date`.

---

## ⚙️ GitHub Actions Automation

The workflow at [`.github/workflows/schedule-updater.yml`](.github/workflows/schedule-updater.yml) runs automatically every trading day:

```
Trigger:  Daily cron at 10:45 UTC (4:30 PM NPT)
          + manual workflow_dispatch
Guard:    Runs are serialized (concurrency group), 3h timeout per job
Steps:    checkout → setup Python 3.10 → install deps from root requirements.txt →
          run runAllScrapers.py → git commit & push data/
```

> No secrets or API keys are required — data is scraped from publicly accessible NEPSE sources.

---

## 🛠️ Dependencies

| Package          | Version   | Purpose                |
|------------------|-----------|------------------------|
| `pandas`         | ≥ 2.2.0   | Data manipulation      |
| `requests`       | ≥ 2.31.0  | HTTP scraping          |
| `lxml`           | ≥ 5.0.0   | HTML/XML parsing       |
| `beautifulsoup4` | ≥ 4.12.0  | HTML parsing           |
| `streamlit`      | ≥ 1.35.0  | Dashboard UI           |
| `plotly`         | ≥ 5.20.0  | Interactive charting   |

---

## 📜 License

This project is open source. Data is sourced from publicly available NEPSE market feeds. Use responsibly and respect the source's terms of service.
# Nepse_data_
