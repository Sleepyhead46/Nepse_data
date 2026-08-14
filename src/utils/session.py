import io
import datetime
import re
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
