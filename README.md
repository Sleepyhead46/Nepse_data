# NEPSE Stock Data & Scraping Suite

An automated, high-performance data scraping suite for the Nepal Stock Exchange (NEPSE). This project collects, processes, and maintains daily, hourly, and minute historical and real-time stock price data for all NEPSE-listed companies, and visualizes them through an interactive Streamlit dashboard.

---

## 📌 Features

- **Multi-Granularity Stock Data**:
  - 📅 **Daily Data** (`data/company-wise/`): Full daily OHLCV historical prices, traded quantities, turnover, and trend status.
  - ⏱️ **Hourly Data** (`data/company-wise-hourly/`): Intra-day hourly snapshots (11:00 AM – 3:00 PM NPT).
  - ⚡ **Minute Data** (`data/company-wise-minute/`): Intra-day minute-level resolution snapshots & backfilled series.
- **Incremental & Idempotent**: Fast tail-scanning and date/timestamp index lookups ensure existing records are never duplicated; re-runs only fetch missing data.
- **Full History Scraping**: Automated pagination and CSRF session handling against ShareSansar's company price history API for 390+ tickers.
- **Intraday Backfill Engine**: Mathematical intra-day price interpolation algorithms to backfill hourly and minute datasets from daily historical data.
- **Interactive Streamlit Dashboard**: Dark-themed visual analytics supporting Daily, Hourly, and Minute resolutions with candlestick/line charts, moving averages, Bollinger Bands, VWAP, Parabolic SAR, RSI, MACD, oscillators, and periodic performance metrics.
- **Company Discovery**: Dynamic discovery script that crawls the live market universe and updates company ID mappings.
- **Automated GitHub Actions**: Scheduled workflow that executes daily at 5:00 PM NPT (after market close) and automatically commits updated datasets.

---

## 📂 Project Structure

```text
nepse-data/
├── .github/
│   └── workflows/
│       └── schedule-updater.yml      # Daily 5:00 PM NPT GitHub Actions cron workflow
├── .streamlit/
│   └── config.toml                   # Streamlit dark theme configuration
├── data/
│   ├── company-wise/                 # Daily CSV files per company ({SYMBOL}.csv)
│   ├── company-wise-hourly/          # Hourly CSV files per company ({SYMBOL}.csv)
│   └── company-wise-minute/          # Minute CSV files per company ({SYMBOL}.csv)
├── src/
│   ├── .streamlit/
│   │   └── config.toml               # Streamlit theme (local dev)
│   ├── config/
│   │   └── headers.py                # HTTP request headers & user-agent configuration
│   ├── constants/
│   │   ├── companyIdMap.py           # Symbol-to-ID mappings (390+ companies)
│   │   └── url.py                    # Target API endpoints
│   ├── utils/
│   │   ├── history.py                # Historical pagination, auth & DataFrame utils
│   │   ├── hourly.py                 # Hourly data schemas & row formatters
│   │   ├── minute.py                 # Minute data schemas & row formatters
│   │   ├── params.py                 # DataTables payload builder
│   │   ├── session.py                # HTTP session factory, CSRF tokens & shared fetchers
│   │   └── status.py                 # Price direction classifier (+1, -1, 0)
│   ├── allDataScrapper.py            # Scrapes entire multi-year daily history (run separately)
│   ├── app.py                        # Streamlit web dashboard for charts & analytics
│   ├── backfillHourlyData.py         # Interpolates daily data into hourly records
│   ├── backfillMinuteData.py         # Interpolates daily data into minute records
│   ├── dailyDataScrapper.py          # Daily market close price scraper
│   ├── discoverCompanies.py          # Discovers new symbols and updates mappings
│   ├── hourlyDataScrapper.py         # Intra-day hourly price scraper
│   ├── minuteDataScrapper.py         # Intra-day minute-level price scraper
│   ├── requirements.txt              # Python dependencies
│   └── runAllScrapers.py             # Master runner: discovery → daily → hourly → minute
└── README.md
```

---

## 📊 Dataset Schema Reference

All data is stored in standard CSV format under `data/` keyed by symbol name (e.g. `ADBL.csv`, `NABIL.csv`).

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

### 2. Hourly Data (`data/company-wise-hourly/{SYMBOL}.csv`)
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

### 3. Minute Data (`data/company-wise-minute/{SYMBOL}.csv`)
| Column | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `published_date` | `string` | Trading date in `YYYY-MM-DD` | `2024-08-14` |
| `timestamp` | `string` | Datetime timestamp with minute resolution | `2024-08-14 11:10:00` |
| `open` | `float` | Interval opening price | `320.00` |
| `high` | `float` | Interval high price | `321.50` |
| `low` | `float` | Interval low price | `319.80` |
| `close` | `float` | Interval closing price | `321.00` |
| `per_change` | `float` | Percentage change from previous interval | `0.31` |
| `traded_quantity`| `float` | Interval volume traded | `1804.8` |
| `traded_amount` | `float` | Interval turnover amount | `581145.6` |
| `status` | `int` | `1` = Gain, `-1` = Loss, `0` = Neutral | `1` |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ recommended
- `pip` package manager

### Installation
```bash
cd nepse-data/src
pip install -r requirements.txt
```

---

## 💻 Usage

### 1. Launch Interactive Dashboard
Launch the visual web dashboard to explore charts, candlestick patterns, moving averages, RSI, and MACD for any NEPSE company across Daily, Hourly, or Minute resolution:
```bash
cd nepse-data/src
streamlit run app.py
```

---

### 2. Run All Scrapers (Automated Data Pipeline)
Executes company discovery, daily close prices, hourly snapshots, and minute snapshots in sequence:
```bash
cd nepse-data/src
python runAllScrapers.py
```

Pipeline steps:
```
[1/4] Discovering New Listed Companies...
[2/4] Running Daily Scraper...
[3/4] Running Hourly Scraper...
[4/4] Running Minute Scraper...
```

---

### Individual Scripts

#### Daily Market Scraper
Fetches today's market closing prices for all listed companies:
```bash
python dailyDataScrapper.py
```

#### Hourly Snapshot Scraper
Captures intra-day hourly snapshots or runs continuously:
```bash
# Single snapshot:
python hourlyDataScrapper.py

# Continuous mode (runs every hour):
python hourlyDataScrapper.py --loop --interval 3600
```

#### Minute Snapshot Scraper
Captures intra-day minute-level snapshots or runs continuously:
```bash
# Single snapshot:
python minuteDataScrapper.py

# Continuous mode (runs every 60s):
python minuteDataScrapper.py --loop --interval 60
```

#### Full Historical Scraper
Fetches complete multi-year history for all 390+ companies (run manually):
```bash
python allDataScrapper.py
```

#### Backfill Hourly Data
Generates hourly records by interpolating daily records:
```bash
python backfillHourlyData.py
```

#### Backfill Minute Data
Generates minute-level records by interpolating daily records:
```bash
python backfillMinuteData.py --step 10
```

#### Discover New Companies
Scrapes the live market universe and updates `companyIdMap.py`:
```bash
python discoverCompanies.py
```

---

## ⚙️ Automated GitHub Actions Workflow

The repository includes a GitHub Actions workflow at `.github/workflows/schedule-updater.yml`.

- **Schedule**: Runs automatically every day at **5:00 PM NPT** (`11:15 UTC`, cron: `15 11 * * *`).
- **Pipeline**: Runs `runAllScrapers.py` (company discovery → daily close update → hourly sync & backfill → minute sync & backfill), then commits and pushes updated data files to the `main` branch.

---

## 🛠️ Data Integrity & Deduplication

- **Atomic Appends**: Scraped entries check the existing file via fast binary tail-checks and timestamp sets to prevent duplicate rows.
- **Sanitized Filenames**: Symbols containing special characters are sanitized into filesystem-safe filenames.
- **Robust Error Handling**: Network retries and CSRF token re-priming prevent interruptions during long scraping sessions.
