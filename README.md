# NEPSE Stock Data & Scraping Suite

An automated, high-performance data scraping and backfilling suite for the Nepal Stock Exchange (NEPSE). This project collects, processes, and maintains daily and hourly historical and real-time stock price data for all NEPSE-listed companies.

---

## 📌 Features

- **Multi-Granularity Stock Data**:
  - 📅 **Daily Data** (`data/company-wise/`): Full daily OHLCV historical prices, traded quantities, turnover, and trend status.
  - ⏱️ **Hourly Data** (`data/company-wise-hourly/`): Intra-day hourly snapshots (11:00 AM – 3:00 PM NPT).
- **Incremental & Idempotent**: Fast tail-scanning and date/timestamp index lookups ensure that existing records are never duplicated and re-runs only fetch missing data.
- **Full History Scraping**: Automated pagination and CSRF session handling against ShareSansar's company price history API for 370+ tickers.
- **Intraday Backfill Engine**: Mathematical intra-day price interpolation algorithms to backfill hourly datasets from daily historical data.
- **Company Discovery**: Dynamic discovery script that crawls the live market universe and updates company ID mappings.
- **Automated GitHub Actions**: Scheduled workflow that executes during NEPSE trading hours (Sun–Thu) and automatically commits updated datasets.

---

## 📂 Project Structure

```text
nepse/
└── nepse-data/
    ├── .github/
    │   └── workflows/
    │       └── schedule-updater.yml      # Hourly GitHub Actions cron workflow
    ├── data/
    │   ├── company-wise/                 # Daily CSV files per company ({SYMBOL}.csv)
    │   └── company-wise-hourly/          # Hourly CSV files per company ({SYMBOL}.csv)
    ├── src/
    │   ├── config/
    │   │   └── headers.py                # HTTP request headers & user-agent configuration
    │   ├── constants/
    │   │   ├── companyIdMap.py           # Symbol-to-ID mappings (370+ companies)
    │   │   └── url.py                    # Target API endpoints
    │   ├── utils/
    │   │   ├── history.py                # Historical pagination, auth & DataFrame utils
    │   │   ├── hourly.py                 # Hourly data schemas & row formatters
    │   │   ├── params.py                 # DataTables payload builder
    │   │   ├── session.py                # HTTP session factory, CSRF tokens & shared fetchers
    │   │   └── status.py                 # Price direction classifier (+1, -1, 0)
    │   ├── allDataScrapper.py            # Scrapes entire multi-year daily history
    │   ├── backfillHourlyData.py         # Interpolates daily data into hourly records
    │   ├── dailyDataScrapper.py          # Daily market close price scraper
    │   ├── discoverCompanies.py          # Discovers new symbols and updates mappings
    │   ├── hourlyDataScrapper.py         # Intra-day hourly price scraper
    │   ├── requirements.txt              # Python dependencies
    │   └── runAllScrapers.py             # Master runner executing daily and hourly scrapers
    └── README.md
```

---

## 📊 Dataset Schema Reference

All data is stored in standard CSV format under `data/` keyed by symbol name (e.g. `ADBL.csv`, `NABIL.csv`, `NRIC.csv`).

### 1. Daily Data (`data/company-wise/{SYMBOL}.csv`)
| Column | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `published_date` | `string` | Trading date in `YYYY-MM-DD` | `2024-08-14` |
| `open` | `float` | Opening price (NPR) | `320.00` |
| `high` | `float` | Highest traded price during the day | `328.50` |
| `low` | `float` | Lowest traded price during the day | `318.00` |
| `close` | `float` | Closing price (NPR) | `325.00` |
| `per_change` | `float` | Percentage change compared to previous close | `1.56` |
| `traded_quantity`| `float` | Total shares traded | `45120.0` |
| `traded_amount` | `float` | Total turnover amount (NPR) | `14664000.0` |
| `status` | `int` | `1` = Bullish / Gain, `-1` = Bearish / Loss, `0` = Neutral | `1` |

### 2. Hourly Data (`data/company-wise-hourly/`)
| Column | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `published_date` | `string` | Trading date in `YYYY-MM-DD` | `2024-08-14` |
| `timestamp` | `string` | Datetime timestamp | `2024-08-14 11:00:00` |
| `open` | `float` | Period opening price | `320.00` |
| `high` | `float` | Period high price | `324.00` |
| `low` | `float` | Period low price | `319.50` |
| `close` | `float` | Period closing price | `322.00` |
| `per_change` | `float` | Percentage change from previous period | `0.62` |
| `traded_quantity`| `float` | Period volume traded | `9024.0` |
| `traded_amount` | `float` | Period turnover amount | `2905728.0` |
| `status` | `int` | `1` = Gain, `-1` = Loss, `0` = Neutral | `1` |

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8+ (Python 3.10+ recommended)
- `pip` package manager

### 2. Installation
Clone the repository and install the dependencies:

```bash
cd nepse-data/src
pip install -r requirements.txt
```

---

## 💻 Usage

### Run All Scrapers (Recommended)
Executes company discovery, daily close, hourly snapshots, and full historical scrapers in one sequence:
```bash
cd nepse-data/src
python runAllScrapers.py
```

---

### Individual Scrapers

#### 1. Daily Market Scraper
Fetches today's market closing prices for all listed companies:
```bash
python dailyDataScrapper.py
```

#### 2. Hourly Snapshot Scraper
Captures current hourly snapshots or runs continuously:
```bash
# Single snapshot:
python hourlyDataScrapper.py

# Continuous mode (runs every hour):
python hourlyDataScrapper.py --loop --interval 3600
```

---

### Historical Data & Utilities

#### 1. Full Historical Scraper (Multi-Year Daily Data)
Fetches all historical data for 370+ companies with auto-token refresh:
```bash
python allDataScrapper.py
```

#### 2. Backfill Hourly Data
Generates hourly records by interpolating daily records:
```bash
python backfillHourlyData.py
```

#### 3. Discover New Companies
Scrapes the live market universe and updates `companyIdMap.py` with newly listed companies:
```bash
python discoverCompanies.py
```

---

## ⚙️ Automated GitHub Actions Workflow

The repository includes a GitHub Actions workflow located at `.github/workflows/schedule-updater.yml`.

- **Schedule**: Runs automatically every hour from **11:00 AM to 3:00 PM NPT** (05:15 to 09:15 UTC) on trading days (**Sunday through Thursday**).
- **Execution**: Runs `runAllScrapers.py`, updates the CSV files under `data/`, and pushes changes to the repository with automated commit messages.

---

## 🛠️ Data Integrity & Deduplication

- **Atomic Appends**: Scraped entries check the existing file via fast binary tail-checks and timestamp sets to prevent duplicate rows.
- **Sanitized Filenames**: Symbols containing special characters are sanitized into filesystem-safe filenames.
- **Robust Error Handling**: Network retries and CSRF token re-priming prevent interruptions during long scraping sessions.

---


# Nepse_data
# Nepse_data
