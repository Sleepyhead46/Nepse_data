import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="NEPSE Stock Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Base Data Directories
BASE_DIR = Path(__file__).resolve().parent.parent
DAILY_DIR = BASE_DIR / "data" / "company-wise"
HOURLY_DIR = BASE_DIR / "data" / "company-wise-hourly"
MINUTE_DIR = BASE_DIR / "data" / "company-wise-minute"

# Apple Design System CSS Injection
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Global Typography & Deep OLED Background */
    html, body, [class*="css"], [class*="st-"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", "Helvetica Neue", sans-serif !important;
        letter-spacing: -0.015em;
    }
    
    .stApp {
        background-color: #000000 !important;
        color: #f5f5f7 !important;
    }

    /* Sidebar Apple Frosted Glass */
    section[data-testid="stSidebar"] {
        background-color: rgba(18, 18, 20, 0.85) !important;
        backdrop-filter: blur(30px) saturate(190%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    /* Apple Glass Card Component */
    .apple-card {
        background: rgba(28, 28, 30, 0.65);
        backdrop-filter: blur(25px) saturate(180%);
        -webkit-backdrop-filter: blur(25px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 8px 24px 0 rgba(0, 0, 0, 0.45);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .apple-card:hover {
        border-color: rgba(255, 255, 255, 0.16);
    }

    .apple-header-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.03em;
        margin: 0;
        line-height: 1.1;
    }
    .apple-header-sub {
        font-size: 0.95rem;
        color: #86868b;
        margin-top: 4px;
        font-weight: 400;
    }

    .apple-price-hero {
        font-size: 3.2rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.04em;
        line-height: 1.1;
    }

    .pill-green {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: rgba(48, 209, 88, 0.15);
        color: #30d158;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 1.05rem;
        font-weight: 600;
        border: 1px solid rgba(48, 209, 88, 0.25);
    }
    .pill-red {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: rgba(255, 69, 58, 0.15);
        color: #ff453a;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 1.05rem;
        font-weight: 600;
        border: 1px solid rgba(255, 69, 58, 0.25);
    }
    .pill-gray {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: rgba(142, 142, 147, 0.15);
        color: #8e8e93;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 1.05rem;
        font-weight: 600;
        border: 1px solid rgba(142, 142, 147, 0.25);
    }

    .stat-label {
        font-size: 0.8rem;
        color: #86868b;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-bottom: 6px;
        font-weight: 500;
    }
    .stat-value {
        font-size: 1.45rem;
        font-weight: 600;
        color: #f5f5f7;
        letter-spacing: -0.02em;
    }
    .stat-sub {
        font-size: 0.82rem;
        color: #a1a1a6;
        margin-top: 3px;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(28, 28, 30, 0.5);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #86868b;
        font-weight: 500;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    
    /* Inputs and Selectors */
    div[data-baseweb="select"] > div {
        background-color: rgba(44, 44, 46, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def get_available_companies():
    """Returns a sorted list of company tickers available in the data directory."""
    if not DAILY_DIR.exists():
        return []
    csv_files = DAILY_DIR.glob("*.csv")
    symbols = sorted([f.stem for f in csv_files if f.is_file()])
    return symbols


@st.cache_data(ttl=300, show_spinner=False)
def load_company_data(symbol: str, granularity: str = "Daily") -> pd.DataFrame:
    """Loads and formats the CSV dataset for a given symbol and granularity."""
    if granularity == "Hourly":
        target_dir = HOURLY_DIR
    elif granularity == "Minute":
        target_dir = MINUTE_DIR
    else:
        target_dir = DAILY_DIR

    file_path = target_dir / f"{symbol}.csv"

    if not file_path.exists():
        return pd.DataFrame()

    df = pd.read_csv(file_path)
    if df.empty:
        return df

    if granularity in ["Hourly", "Minute"] and "timestamp" in df.columns:
        df["datetime"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="datetime").reset_index(drop=True)
    else:
        df["datetime"] = pd.to_datetime(df["published_date"])
        df = df.sort_values(by="datetime").reset_index(drop=True)

    # Convert numerical columns
    num_cols = ["open", "high", "low", "close", "per_change", "traded_quantity", "traded_amount"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Computes technical analysis indicators: SMAs, EMAs, Bollinger Bands, VWAP,
    Parabolic SAR, RSI, MACD, Stochastic, ATR, CCI, Williams %R, OBV."""
    if len(df) < 5:
        return df

    data = df.copy()

    # --- Moving Averages ---
    data["SMA20"]  = data["close"].rolling(window=20).mean()
    data["SMA50"]  = data["close"].rolling(window=50).mean()
    data["SMA200"] = data["close"].rolling(window=200).mean()
    data["EMA20"]  = data["close"].ewm(span=20, adjust=False).mean()
    data["EMA50"]  = data["close"].ewm(span=50, adjust=False).mean()

    # --- Bollinger Bands (20, 2) ---
    std20 = data["close"].rolling(window=20).std()
    data["BB_Upper"] = data["SMA20"] + (std20 * 2)
    data["BB_Lower"] = data["SMA20"] - (std20 * 2)

    # --- VWAP (cumulative intraday; resets per session via date grouping) ---
    if "traded_amount" in data.columns and "traded_quantity" in data.columns:
        data["_pv"] = data["traded_amount"]
        data["_vol"] = data["traded_quantity"].replace(0, np.nan)
        data["VWAP"] = data["_pv"].cumsum() / data["_vol"].cumsum()
        data.drop(columns=["_pv", "_vol"], inplace=True)

    # --- Parabolic SAR ---
    af_step, af_max = 0.02, 0.20
    high = data["high"].values
    low  = data["low"].values
    n = len(data)
    sar = np.full(n, np.nan)
    ep  = np.full(n, np.nan)
    af  = np.full(n, af_step)
    bull = True
    sar[0] = low[0]
    ep[0]  = high[0]
    for i in range(1, n):
        prev_sar = sar[i - 1]
        prev_ep  = ep[i - 1]
        prev_af  = af[i - 1]
        if bull:
            sar[i] = prev_sar + prev_af * (prev_ep - prev_sar)
            sar[i] = min(sar[i], low[i - 1], low[i - 2] if i > 1 else low[i - 1])
            if high[i] > prev_ep:
                ep[i] = high[i]
                af[i] = min(prev_af + af_step, af_max)
            else:
                ep[i] = prev_ep
                af[i] = prev_af
            if low[i] < sar[i]:  # reversal
                bull = False
                sar[i] = prev_ep
                ep[i]  = low[i]
                af[i]  = af_step
        else:
            sar[i] = prev_sar - prev_af * (prev_sar - prev_ep)
            sar[i] = max(sar[i], high[i - 1], high[i - 2] if i > 1 else high[i - 1])
            if low[i] < prev_ep:
                ep[i] = low[i]
                af[i] = min(prev_af + af_step, af_max)
            else:
                ep[i] = prev_ep
                af[i] = prev_af
            if high[i] > sar[i]:  # reversal
                bull = True
                sar[i] = prev_ep
                ep[i]  = high[i]
                af[i]  = af_step
    data["PSAR"] = sar

    # --- RSI (14) ---
    delta = data["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data["RSI14"] = 100 - (100 / (1 + rs))

    # --- MACD (12, 26, 9) ---
    ema12 = data["close"].ewm(span=12, adjust=False).mean()
    ema26 = data["close"].ewm(span=26, adjust=False).mean()
    data["MACD"]        = ema12 - ema26
    data["MACD_Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["MACD_Hist"]   = data["MACD"] - data["MACD_Signal"]

    # --- Stochastic Oscillator (14, 3) ---
    low14  = data["low"].rolling(14).min()
    high14 = data["high"].rolling(14).max()
    data["STOCH_K"] = 100 * (data["close"] - low14) / (high14 - low14)
    data["STOCH_D"] = data["STOCH_K"].rolling(3).mean()

    # --- ATR (14) ---
    prev_close = data["close"].shift(1)
    tr = pd.concat([
        data["high"] - data["low"],
        (data["high"] - prev_close).abs(),
        (data["low"]  - prev_close).abs(),
    ], axis=1).max(axis=1)
    data["ATR14"] = tr.ewm(span=14, adjust=False).mean()

    # --- CCI (20) ---
    tp = (data["high"] + data["low"] + data["close"]) / 3
    tp_sma = tp.rolling(20).mean()
    tp_std = tp.rolling(20).std()
    data["CCI20"] = (tp - tp_sma) / (0.015 * tp_std)

    # --- Williams %R (14) ---
    data["WILLR"] = -100 * (high14 - data["close"]) / (high14 - low14)

    # --- OBV (On-Balance Volume) ---
    obv = [0]
    for i in range(1, len(data)):
        if data["close"].iloc[i] > data["close"].iloc[i - 1]:
            obv.append(obv[-1] + data["traded_quantity"].iloc[i])
        elif data["close"].iloc[i] < data["close"].iloc[i - 1]:
            obv.append(obv[-1] - data["traded_quantity"].iloc[i])
        else:
            obv.append(obv[-1])
    data["OBV"] = obv

    return data


# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("### 📈 **NEPSE Stocks**")
st.sidebar.caption("Nepal Stock Exchange Analytics")

symbols = get_available_companies()
if not symbols:
    st.error("No stock datasets found in `data/company-wise/`. Please run scrapers first.")
    st.stop()

# Default to NABIL or first symbol
default_index = symbols.index("NABIL") if "NABIL" in symbols else 0
selected_symbol = st.sidebar.selectbox("Symbol / Ticker", symbols, index=default_index)

granularity = st.sidebar.radio("Granularity", ["Daily", "Hourly", "Minute"], horizontal=True)

# Timeframe Filter
st.sidebar.markdown("#### **Date Range**")
_TIMEFRAME_LABELS = {
    "1 Month":    "1M",
    "3 Months":   "3M",
    "6 Months":   "6M",
    "Year to Date": "YTD",
    "1 Year":     "1Y",
    "3 Years":    "3Y",
    "5 Years":    "5Y",
    "All Time":   "All",
    "Custom Range": "Custom",
}
_tf_display = st.sidebar.radio(
    "Preset",
    list(_TIMEFRAME_LABELS.keys()),
    index=4,
    label_visibility="collapsed",
)
selected_timeframe = _TIMEFRAME_LABELS[_tf_display]

custom_date_range = None
if selected_timeframe == "Custom":
    today = datetime.date.today()
    one_year_ago = today - datetime.timedelta(days=365)
    st.sidebar.markdown("**From / To Date**")
    col_from, col_to = st.sidebar.columns(2)
    with col_from:
        custom_start = st.date_input("From", value=one_year_ago, max_value=today, key="custom_from")
    with col_to:
        custom_end = st.date_input("To", value=today, min_value=custom_start, max_value=today, key="custom_to")
    custom_date_range = (custom_start, custom_end)

# Technical Indicators Toggles
st.sidebar.markdown("---")
st.sidebar.markdown("#### **Overlays**")
chart_type = st.sidebar.radio("Style", ["Candlestick", "Line"], horizontal=True)
show_sma20  = st.sidebar.checkbox("SMA 20  — short trend", value=True)
show_sma50  = st.sidebar.checkbox("SMA 50  — mid trend", value=False)
show_sma200 = st.sidebar.checkbox("SMA 200 — long trend", value=False)
show_ema20  = st.sidebar.checkbox("EMA 20  — reactive short", value=False)
show_ema50  = st.sidebar.checkbox("EMA 50  — reactive mid", value=False)
show_bb     = st.sidebar.checkbox("Bollinger Bands (20, 2)", value=False)
show_vwap   = st.sidebar.checkbox("VWAP — avg price by volume", value=False)
show_psar   = st.sidebar.checkbox("Parabolic SAR — trend dots", value=False)

st.sidebar.markdown("#### **Oscillators**")
show_volume = st.sidebar.checkbox("Volume Histogram", value=True)
show_rsi    = st.sidebar.checkbox("RSI (14) — momentum", value=True)
show_macd   = st.sidebar.checkbox("MACD (12,26,9) — trend strength", value=False)
show_stoch  = st.sidebar.checkbox("Stochastic (14,3) — overbought/sold", value=False)
show_atr    = st.sidebar.checkbox("ATR (14) — volatility", value=False)
show_cci    = st.sidebar.checkbox("CCI (20) — cycle", value=False)
show_willr  = st.sidebar.checkbox("Williams %R (14)", value=False)
show_obv    = st.sidebar.checkbox("OBV — volume momentum", value=False)


# --- DATA LOADING & FILTERING ---
raw_df = load_company_data(selected_symbol, granularity)

if raw_df.empty:
    st.warning(f"No {granularity.lower()} data available for symbol '{selected_symbol}'.")
    st.stop()

df = calculate_technical_indicators(raw_df)

# Filter by Date Range
max_date = df["datetime"].max()
if selected_timeframe == "1M":
    start_date = max_date - pd.DateOffset(months=1)
elif selected_timeframe == "3M":
    start_date = max_date - pd.DateOffset(months=3)
elif selected_timeframe == "6M":
    start_date = max_date - pd.DateOffset(months=6)
elif selected_timeframe == "YTD":
    start_date = pd.Timestamp(year=max_date.year, month=1, day=1)
elif selected_timeframe == "1Y":
    start_date = max_date - pd.DateOffset(years=1)
elif selected_timeframe == "3Y":
    start_date = max_date - pd.DateOffset(years=3)
elif selected_timeframe == "5Y":
    start_date = max_date - pd.DateOffset(years=5)
elif selected_timeframe == "Custom" and custom_date_range and len(custom_date_range) == 2:
    start_date = pd.Timestamp(custom_date_range[0])
    max_date = pd.Timestamp(custom_date_range[1])
else:
    start_date = df["datetime"].min()

filtered_df = df[(df["datetime"] >= start_date) & (df["datetime"] <= max_date)].copy()
if filtered_df.empty:
    st.warning("No records in selected timeframe. Showing full dataset instead.")
    filtered_df = df.copy()


# --- TOP APPLE HERO CARD & METRICS ---
latest_row = filtered_df.iloc[-1]
prev_row = filtered_df.iloc[-2] if len(filtered_df) > 1 else latest_row

close_price = latest_row.get("close", 0.0)
prev_close = prev_row.get("close", close_price)
price_change = close_price - prev_close
pct_change = (price_change / prev_close * 100) if prev_close else 0.0

period_high = filtered_df["high"].max()
period_low = filtered_df["low"].min()
total_volume = filtered_df["traded_quantity"].sum()
total_turnover = filtered_df["traded_amount"].sum()

# 52-week High/Low from full history
one_year_ago = df["datetime"].max() - pd.DateOffset(years=1)
df_52w = df[df["datetime"] >= one_year_ago]
high_52w = df_52w["high"].max() if not df_52w.empty else period_high
low_52w = df_52w["low"].min() if not df_52w.empty else period_low

if price_change > 0:
    pill_html = f'<div class="pill-green">▲ +Rs. {price_change:,.2f} (+{pct_change:.2f}%)</div>'
elif price_change < 0:
    pill_html = f'<div class="pill-red">▼ -Rs. {abs(price_change):,.2f} ({pct_change:.2f}%)</div>'
else:
    pill_html = '<div class="pill-gray">━ Rs. 0.00 (0.00%)</div>'

date_str = latest_row['datetime'].strftime('%b %d, %Y · %I:%M %p' if granularity in ['Hourly', 'Minute'] else '%b %d, %Y')

# Render Apple Hero Header Card
st.markdown(
    f"""
    <div class="apple-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
            <div>
                <h1 class="apple-header-title">{selected_symbol}</h1>
                <div class="apple-header-sub">Nepal Stock Exchange · {granularity} Resolution · {date_str}</div>
                <div style="margin-top: 14px; display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap;">
                    <span class="apple-price-hero">Rs. {close_price:,.2f}</span>
                    {pill_html}
                </div>
            </div>
            <div style="display: flex; gap: 28px; flex-wrap: wrap; align-items: center;">
                <div>
                    <div class="stat-label">Range ({selected_timeframe})</div>
                    <div class="stat-value">Rs. {period_high:,.1f}</div>
                    <div class="stat-sub">Low: Rs. {period_low:,.1f}</div>
                </div>
                <div>
                    <div class="stat-label">52-Week High/Low</div>
                    <div class="stat-value">Rs. {high_52w:,.1f}</div>
                    <div class="stat-sub">Low: Rs. {low_52w:,.1f}</div>
                </div>
                <div>
                    <div class="stat-label">Volume / Turnover</div>
                    <div class="stat-value">{total_volume:,.0f} sh</div>
                    <div class="stat-sub">Rs. {total_turnover/1e6:,.2f}M</div>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- MAIN DASHBOARD TABS ---
tab_chart, tab_stats, tab_data = st.tabs(["📈 Chart & Indicators", "📊 Performance", "📋 Data Table"])

with tab_chart:
    # Determine subplot rows
    rows = 1
    row_heights = [0.55]
    specs = [[{"secondary_y": False}]]

    _osc_height = 0.16
    for _show in [show_volume, show_rsi, show_macd, show_stoch, show_atr, show_cci, show_willr, show_obv]:
        if _show:
            rows += 1
            row_heights.append(_osc_height)
            specs.append([{"secondary_y": False}])

    # Normalize row heights
    total_h = sum(row_heights)
    row_heights = [h / total_h for h in row_heights]

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=row_heights,
    )

    current_row = 1

    # 1. Main Price Chart (Apple Candlestick or Apple Line)
    if chart_type == "Candlestick":
        fig.add_trace(
            go.Candlestick(
                x=filtered_df["datetime"],
                open=filtered_df["open"],
                high=filtered_df["high"],
                low=filtered_df["low"],
                close=filtered_df["close"],
                name="OHLC",
                increasing_line_color="#30d158",
                increasing_fillcolor="#30d158",
                decreasing_line_color="#ff453a",
                decreasing_fillcolor="#ff453a",
            ),
            row=current_row,
            col=1,
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=filtered_df["datetime"],
                y=filtered_df["close"],
                mode="lines",
                name="Price",
                line=dict(color="#0a84ff", width=2.2),
            ),
            row=current_row,
            col=1,
        )

    # Overlays
    if show_sma20 and "SMA20" in filtered_df.columns:
        fig.add_trace(
            go.Scatter(x=filtered_df["datetime"], y=filtered_df["SMA20"], mode="lines", name="SMA 20", line=dict(color="#ffd60a", width=1.4)),
            row=current_row,
            col=1,
        )
    if show_sma50 and "SMA50" in filtered_df.columns:
        fig.add_trace(
            go.Scatter(x=filtered_df["datetime"], y=filtered_df["SMA50"], mode="lines", name="SMA 50", line=dict(color="#ff9f0a", width=1.4)),
            row=current_row,
            col=1,
        )
    if show_sma200 and "SMA200" in filtered_df.columns:
        fig.add_trace(
            go.Scatter(x=filtered_df["datetime"], y=filtered_df["SMA200"], mode="lines", name="SMA 200", line=dict(color="#bf5af2", width=1.4)),
            row=current_row,
            col=1,
        )
    if show_ema20 and "EMA20" in filtered_df.columns:
        fig.add_trace(
            go.Scatter(x=filtered_df["datetime"], y=filtered_df["EMA20"], mode="lines", name="EMA 20", line=dict(color="#64d2ff", width=1.4, dash="dot")),
            row=current_row, col=1,
        )
    if show_ema50 and "EMA50" in filtered_df.columns:
        fig.add_trace(
            go.Scatter(x=filtered_df["datetime"], y=filtered_df["EMA50"], mode="lines", name="EMA 50", line=dict(color="#5ac8fa", width=1.4, dash="dashdot")),
            row=current_row, col=1,
        )
    if show_bb and "BB_Upper" in filtered_df.columns:
        fig.add_trace(
            go.Scatter(x=filtered_df["datetime"], y=filtered_df["BB_Upper"], mode="lines", name="BB Upper", line=dict(color="rgba(142, 142, 147, 0.4)", width=1)),
            row=current_row, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=filtered_df["datetime"], y=filtered_df["BB_Lower"],
                mode="lines", name="BB Lower",
                fill="tonexty", fillcolor="rgba(142, 142, 147, 0.06)",
                line=dict(color="rgba(142, 142, 147, 0.4)", width=1),
            ),
            row=current_row, col=1,
        )
    if show_vwap and "VWAP" in filtered_df.columns:
        fig.add_trace(
            go.Scatter(x=filtered_df["datetime"], y=filtered_df["VWAP"], mode="lines", name="VWAP", line=dict(color="#ff375f", width=1.6, dash="dot")),
            row=current_row, col=1,
        )
    if show_psar and "PSAR" in filtered_df.columns:
        psar_colors = [
            "#30d158" if p < c else "#ff453a"
            for p, c in zip(filtered_df["PSAR"], filtered_df["close"])
        ]
        fig.add_trace(
            go.Scatter(
                x=filtered_df["datetime"], y=filtered_df["PSAR"],
                mode="markers", name="Parabolic SAR",
                marker=dict(color=psar_colors, size=3, symbol="circle"),
            ),
            row=current_row, col=1,
        )

    fig.update_yaxes(
        title_text="NPR",
        row=current_row,
        col=1,
        gridcolor="rgba(255, 255, 255, 0.06)",
        zerolinecolor="rgba(255, 255, 255, 0.08)",
    )

    # 2. Volume Subplot
    if show_volume:
        current_row += 1
        vol_colors = [
            "#30d158" if c >= o else "#ff453a"
            for c, o in zip(filtered_df["close"], filtered_df["open"])
        ]
        fig.add_trace(
            go.Bar(
                x=filtered_df["datetime"],
                y=filtered_df["traded_quantity"],
                name="Volume",
                marker_color=vol_colors,
                opacity=0.75,
            ),
            row=current_row,
            col=1,
        )
        fig.update_yaxes(
            title_text="Vol",
            row=current_row,
            col=1,
            gridcolor="rgba(255, 255, 255, 0.06)",
            zerolinecolor="rgba(255, 255, 255, 0.08)",
        )

    # 3. RSI Subplot
    if show_rsi:
        current_row += 1
        fig.add_trace(
            go.Scatter(
                x=filtered_df["datetime"],
                y=filtered_df["RSI14"],
                name="RSI 14",
                line=dict(color="#bf5af2", width=1.5),
            ),
            row=current_row,
            col=1,
        )
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(255, 69, 58, 0.45)", row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(48, 209, 88, 0.45)", row=current_row, col=1)
        fig.update_yaxes(
            title_text="RSI",
            range=[0, 100],
            row=current_row,
            col=1,
            gridcolor="rgba(255, 255, 255, 0.06)",
            zerolinecolor="rgba(255, 255, 255, 0.08)",
        )

    # 4. MACD Subplot
    if show_macd:
        current_row += 1
        fig.add_trace(
            go.Scatter(
                x=filtered_df["datetime"],
                y=filtered_df["MACD"],
                name="MACD",
                line=dict(color="#0a84ff", width=1.5),
            ),
            row=current_row,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=filtered_df["datetime"],
                y=filtered_df["MACD_Signal"],
                name="Signal",
                line=dict(color="#ff9f0a", width=1.5),
            ),
            row=current_row,
            col=1,
        )
        macd_colors = ["#30d158" if val >= 0 else "#ff453a" for val in filtered_df["MACD_Hist"]]
        fig.add_trace(
            go.Bar(
                x=filtered_df["datetime"],
                y=filtered_df["MACD_Hist"],
                name="Histogram",
                marker_color=macd_colors,
                opacity=0.7,
            ),
            row=current_row,
            col=1,
        )
        fig.update_yaxes(
            title_text="MACD",
            row=current_row,
            col=1,
            gridcolor="rgba(255, 255, 255, 0.06)",
            zerolinecolor="rgba(255, 255, 255, 0.08)",
        )

    # 5. Stochastic Subplot
    if show_stoch:
        current_row += 1
        fig.add_trace(
            go.Scatter(x=filtered_df["datetime"], y=filtered_df["STOCH_K"], name="%K", line=dict(color="#ffd60a", width=1.5)),
            row=current_row, col=1,
        )
        fig.add_trace(
            go.Scatter(x=filtered_df["datetime"], y=filtered_df["STOCH_D"], name="%D", line=dict(color="#ff9f0a", width=1.5, dash="dot")),
            row=current_row, col=1,
        )
        fig.add_hline(y=80, line_dash="dash", line_color="rgba(255,69,58,0.35)", row=current_row, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="rgba(48,209,88,0.35)", row=current_row, col=1)
        fig.update_yaxes(title_text="Stoch", range=[0, 100], row=current_row, col=1,
                         gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)")

    # 6. ATR Subplot
    if show_atr:
        current_row += 1
        fig.add_trace(
            go.Scatter(x=filtered_df["datetime"], y=filtered_df["ATR14"], name="ATR 14", line=dict(color="#ff9f0a", width=1.5), fill="tozeroy", fillcolor="rgba(255,159,10,0.08)"),
            row=current_row, col=1,
        )
        fig.update_yaxes(title_text="ATR", row=current_row, col=1,
                         gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)")

    # 7. CCI Subplot
    if show_cci:
        current_row += 1
        cci_colors = ["#30d158" if v >= 0 else "#ff453a" for v in filtered_df["CCI20"].fillna(0)]
        fig.add_trace(
            go.Bar(x=filtered_df["datetime"], y=filtered_df["CCI20"], name="CCI 20", marker_color=cci_colors, opacity=0.75),
            row=current_row, col=1,
        )
        fig.add_hline(y=100,  line_dash="dash", line_color="rgba(255,69,58,0.35)",  row=current_row, col=1)
        fig.add_hline(y=-100, line_dash="dash", line_color="rgba(48,209,88,0.35)",  row=current_row, col=1)
        fig.update_yaxes(title_text="CCI", row=current_row, col=1,
                         gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)")

    # 8. Williams %R Subplot
    if show_willr:
        current_row += 1
        fig.add_trace(
            go.Scatter(x=filtered_df["datetime"], y=filtered_df["WILLR"], name="%R", line=dict(color="#64d2ff", width=1.5)),
            row=current_row, col=1,
        )
        fig.add_hline(y=-20,  line_dash="dash", line_color="rgba(255,69,58,0.35)",  row=current_row, col=1)
        fig.add_hline(y=-80,  line_dash="dash", line_color="rgba(48,209,88,0.35)",  row=current_row, col=1)
        fig.update_yaxes(title_text="W%R", range=[-100, 0], row=current_row, col=1,
                         gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)")

    # 9. OBV Subplot
    if show_obv:
        current_row += 1
        fig.add_trace(
            go.Scatter(x=filtered_df["datetime"], y=filtered_df["OBV"], name="OBV", line=dict(color="#5e5ce6", width=1.5), fill="tozeroy", fillcolor="rgba(94,92,230,0.08)"),
            row=current_row, col=1,
        )
        fig.update_yaxes(title_text="OBV", row=current_row, col=1,
                         gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)")

    # Clean Apple Plotly Layout
    chart_height = 520 + (rows - 1) * 150
    fig.update_xaxes(
        gridcolor="rgba(255, 255, 255, 0.04)",
        zerolinecolor="rgba(255, 255, 255, 0.08)",
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikethickness=1,
        spikecolor="rgba(255, 255, 255, 0.2)",
    )
    fig.update_layout(
        height=chart_height,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        paper_bgcolor="#000000",
        plot_bgcolor="#0a0a0c",
        margin=dict(l=55, r=20, t=25, b=25),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
            font=dict(color="#86868b", size=11),
            bgcolor="rgba(0, 0, 0, 0)",
        ),
        font=dict(family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif", color="#86868b"),
    )

    st.plotly_chart(fig, use_container_width=True)

with tab_stats:
    st.markdown("### 📊 **Returns & Historical Performance**")

    # Periodic returns calculation helper
    def get_period_return(days):
        cutoff = max_date - pd.DateOffset(days=days)
        sub_df = df[df["datetime"] >= cutoff]
        if len(sub_df) >= 2:
            start_p = sub_df.iloc[0]["close"]
            end_p = sub_df.iloc[-1]["close"]
            if start_p > 0:
                return ((end_p - start_p) / start_p) * 100
        return None

    periods = [("1W", 7), ("1M", 30), ("3M", 90), ("6M", 180), ("1Y", 365), ("3Y", 365 * 3)]
    cols = st.columns(len(periods))

    for col, (label, days) in zip(cols, periods):
        ret = get_period_return(days)
        with col:
            st.markdown(
                f"""
                <div class="apple-card" style="text-align: center; padding: 16px;">
                    <div class="stat-label">{label} Return</div>
                    <div class="stat-value" style="color: {'#30d158' if ret and ret >= 0 else '#ff453a' if ret else '#8e8e93'}; font-size: 1.35rem;">
                        {f"{ret:+.2f}%" if ret is not None else "—"}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("### 📐 **Statistical Overview**")
    stat_summary = filtered_df[["open", "high", "low", "close", "traded_quantity", "traded_amount"]].describe().T
    stat_summary.columns = ["Count", "Mean", "Std Dev", "Min", "25%", "Median", "75%", "Max"]
    st.dataframe(stat_summary.style.format("{:,.2f}"), use_container_width=True)

with tab_data:
    st.markdown(f"### 📋 **Data Records — {selected_symbol}**")

    display_cols = [
        col for col in ["published_date", "timestamp", "open", "high", "low", "close", "per_change", "traded_quantity", "traded_amount", "status"]
        if col in filtered_df.columns
    ]

    csv_export = filtered_df[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export CSV",
        data=csv_export,
        file_name=f"{selected_symbol}_{granularity.lower()}_{start_date.strftime('%Y%m%d')}_{max_date.strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

    st.dataframe(
        filtered_df[display_cols].sort_values(by="timestamp" if "timestamp" in display_cols else "published_date", ascending=False).reset_index(drop=True),
        use_container_width=True,
        height=500,
    )
