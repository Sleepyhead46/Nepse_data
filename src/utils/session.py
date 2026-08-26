import io
import datetime
import os
import re
import threading
import pandas as pd
import requests
from bs4 import BeautifulSoup
from config.headers import headers
from constants.url import dailyPriceUrl

_TOKEN_RE = re.compile(r'name="_token"\s+value="([^"]+)"')
_COMPANYID_RE = re.compile(r'id="companyid"[^>]*>\s*([0-9]+)')

BASE = "https://www.sharesansar.com"
TIMEOUT = 30  # seconds; a throttled server may hold the connection open


def extract_token(html):
    m = _TOKEN_RE.search(html)
    return m.group(1) if m else None


def extract_companyid(html):
    m = _COMPANYID_RE.search(html)
    return m.group(1) if m else None


def make_session():
    session = requests.Session()
    session.headers.update(headers)
    return session


def prime_session(session, symbol="adbl"):
    resp = session.get(f"{BASE}/company/{symbol.lower()}", timeout=TIMEOUT)
    resp.raise_for_status()
    return extract_token(resp.text)


def fetch_today_share_prices(session=None):
    """Fetches and parses live/today share prices from ShareSansar."""
    if session is None:
        session = make_session()

    resp = session.get(dailyPriceUrl, timeout=TIMEOUT)
    resp.raise_for_status()

    bs = BeautifulSoup(resp.text, "lxml")
    date_element = bs.find("span", {"class": "text-org"})
    today_date = date_element.text.strip() if date_element else datetime.datetime.now().strftime("%Y-%m-%d")

    tables = pd.read_html(io.StringIO(resp.text))
    if not tables:
        raise ValueError("No price tables found in ShareSansar response.")

    return today_date, tables[0]


# ---------------------------------------------------------------------------
# Parallel scraping support
# ---------------------------------------------------------------------------

# Number of parallel company workers (network-bound, so threads scale well).
# Override with e.g. SCRAPERS_WORKERS=4 to be extra polite to the source site.
WORKERS = max(1, int(os.environ.get("SCRAPERS_WORKERS", "8")))

_thread_local = threading.local()


def get_thread_scraper():
    """Returns THIS thread's own (session, csrf-token) pair, creating and
    priming it on first use.

    ShareSansar's CSRF token is bound to the Laravel session cookie stored on
    the requests.Session, so concurrent workers must never share a single
    session - each thread primes (and later refreshes) its own pair."""
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = make_session()
        try:
            token = prime_session(session)
        except requests.RequestException:
            token = None
        _thread_local.session = session
        _thread_local.token = token
    return session, getattr(_thread_local, "token", None)


def set_thread_token(token):
    """Stores the refreshed CSRF token for the calling thread's session."""
    _thread_local.token = token
