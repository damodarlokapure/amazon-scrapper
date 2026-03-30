BOT_NAME = "scraper"

SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

from config import config

# Expose config defaults into Scrapy settings so they can be overridden via run-time settings.
TARGET_ASINS = config.TARGET_ASINS
TARGET_MODELS = config.TARGET_MODELS
SEARCH_BRAND = config.SEARCH_BRAND
SEARCH_PAGES = config.SEARCH_PAGES
DEFAULT_MARGIN_PCT = config.DEFAULT_MARGIN_PCT
YOUR_PRICE_BY_ASIN = config.YOUR_PRICE_BY_ASIN

SCRAPEOPS_API_KEY = config.SCRAPEOPS_API_KEY

# ❌ Ignore robots.txt (needed for Amazon scraping)
ROBOTSTXT_OBEY = False


# 🔥 Downloader Middlewares (User-Agent rotation)
DOWNLOADER_MIDDLEWARES = {
    "scraper.middlewares.GeoHeaderMiddleware": 350,
    "scraper.middlewares.RandomUserAgentMiddleware": 400,
    "scraper.middlewares.ProxyRotationMiddleware": 500,
    "scraper.middlewares.ScrapeOpsProxyMiddleware": 520,
}


# 🔥 Pipelines (MySQL storage)
ITEM_PIPELINES = {
    "scraper.pipelines.MySQLPipeline": 300,
}


# ⚡ Concurrency settings (important for product page scraping)
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2


# 🐢 Throttling (VERY IMPORTANT to avoid blocking)
DOWNLOAD_DELAY = 3

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10


# 🌐 Headers to mimic real browser
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


# 🧠 Logging
LOG_LEVEL = "INFO"


# Proxy/ScrapeOps toggles
SCRAPEOPS_API_KEY = SCRAPEOPS_API_KEY