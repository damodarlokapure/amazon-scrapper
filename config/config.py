import json
import os
from typing import Dict, List

from dotenv import load_dotenv


load_dotenv()


def _env_list(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [part.strip() for part in raw.split(",") if part.strip()]


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_price_map(name: str, default: Dict[str, float]) -> Dict[str, float]:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        loaded = json.loads(raw)
        if isinstance(loaded, dict):
            return {k: float(v) for k, v in loaded.items()}
    except Exception:
        pass
    return default


DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root123"),
    "database": os.getenv("DB_NAME", "amazon_monitor"),
}

# ASINs to monitor  env override: TARGET_ASINS="ASIN1,ASIN2"
TARGET_ASINS = _env_list(
    "TARGET_ASINS",
    [
        "B07H1GJZMP",   # SKF bearing
        "B07H88MND1",   # Ball Bearing 6206
        "B07H889LJK",   # Ball Bearing 6302
    ],
)

# Search workflow configuration (env overrides: TARGET_MODELS, SEARCH_BRAND, SEARCH_PAGES)
SEARCH_BRAND = os.getenv("SEARCH_BRAND", "SKF")
TARGET_MODELS = _env_list("TARGET_MODELS", ["6206", "6302", "6205"])
SEARCH_PAGES = _env_int("SEARCH_PAGES", 3)

# Pricing strategy used for summary metrics (env override: DEFAULT_MARGIN_PCT, YOUR_PRICE_BY_ASIN_JSON)
DEFAULT_MARGIN_PCT = _env_float("DEFAULT_MARGIN_PCT", 2.0)
YOUR_PRICE_BY_ASIN = _env_price_map(
    "YOUR_PRICE_BY_ASIN_JSON",
    {
        "B07H1GJZMP": 2249.0,
        "B07H88MND1": 1899.0,
        "B07H889LJK": 999.0,
    },
)

# ScrapeOps + proxy rotation configuration
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY", "")
PROXY_POOL = [p.strip() for p in os.getenv("PROXY_POOL", "").split(",") if p.strip()]
MIN_PROXY_POOL_SIZE = _env_int("MIN_PROXY_POOL_SIZE", 100)

# Tamil Nadu PIN codes to simulate different locations
TN_PINCODES = _env_list(
    "TN_PINCODES",
    [
        "600001",   # Chennai
        "641001",   # Coimbatore
        "625001",   # Madurai
        "620001",   # Tiruchirappalli
        "630001",   # Sivakasi
    ],
)