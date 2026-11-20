"""
Официальный курс НБКР (https://www.nbkr.kg/XML/daily.xml) для пересчёта цен USD ↔ KGS.
Курс кэшируется на 3 часа; при сбое НБКР отдаётся последний удачный курс (до 3 суток).
"""
import logging
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from urllib.request import Request, urlopen

from django.core.cache import cache

logger = logging.getLogger(__name__)

NBKR_DAILY_URL = "https://www.nbkr.kg/XML/daily.xml"
CACHE_KEY = "nbkr_rates"
STALE_CACHE_KEY = "nbkr_rates_stale"
CACHE_SECONDS = 3 * 60 * 60
STALE_CACHE_SECONDS = 3 * 24 * 60 * 60


def parse_nbkr_xml(content):
    """{'date': '21.11.2026', 'rates': {'USD': '87.4500', ...}} — сом за 1 единицу валюты."""
    root = ET.fromstring(content)
    rates = {}
    for currency in root.findall("Currency"):
        code = currency.get("ISOCode")
        try:
            nominal = Decimal(currency.findtext("Nominal", "1").replace(",", "."))
            value = Decimal(currency.findtext("Value", "").replace(",", "."))
        except (InvalidOperation, AttributeError):
            continue
        if code and nominal > 0 and value > 0:
            rates[code] = str((value / nominal).quantize(Decimal("0.0001")))
    if "USD" not in rates:
        raise ValueError("В ответе НБКР нет курса USD")
    return {"date": root.get("Date"), "rates": rates, "source": "НБКР"}


def fetch_nbkr_rates(timeout=10):
    request = Request(NBKR_DAILY_URL, headers={"User-Agent": "Mozilla/5.0 (rates client)"})
    with urlopen(request, timeout=timeout) as response:
        return parse_nbkr_xml(response.read())


def get_rates():
    data = cache.get(CACHE_KEY)
    if data:
        return data
    try:
        data = fetch_nbkr_rates()
    except Exception:
        logger.warning("Не удалось получить курс НБКР", exc_info=True)
        return cache.get(STALE_CACHE_KEY)
    cache.set(CACHE_KEY, data, CACHE_SECONDS)
    cache.set(STALE_CACHE_KEY, data, STALE_CACHE_SECONDS)
    return data
