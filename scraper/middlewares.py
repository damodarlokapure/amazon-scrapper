import random
from urllib.parse import urlencode

from fake_useragent import UserAgent

from config.config import MIN_PROXY_POOL_SIZE, PROXY_POOL, SCRAPEOPS_API_KEY, TN_PINCODES


class RandomUserAgentMiddleware:
    def __init__(self):
        self.ua = UserAgent()

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider=None):
        request.headers["User-Agent"] = self.ua.random


class GeoHeaderMiddleware:
    """Adds India-focused headers and a rotating TN postal code hint."""

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider=None):
        pincode = request.meta.get("pincode") or random.choice(TN_PINCODES)
        request.meta["pincode"] = pincode
        request.headers["Accept-Language"] = "en-IN,en;q=0.9"
        request.headers["x-amz-user-postal-code"] = pincode
        request.headers["x-forwarded-for"] = self._to_mock_indian_ip(pincode)

    @staticmethod
    def _to_mock_indian_ip(pincode):
        # Deterministic-ish mock IP by pincode to vary geo signals per request.
        tail = int(pincode[-3:])
        return f"49.{(tail % 250) + 1}.{((tail * 3) % 250) + 1}.{((tail * 7) % 250) + 1}"


class ProxyRotationMiddleware:
    """Rotates raw proxies from PROXY_POOL env var."""

    def __init__(self):
        self.pool = PROXY_POOL
        self._warned = False

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider=None):
        if not self.pool:
            return
        if len(self.pool) < MIN_PROXY_POOL_SIZE and not self._warned and spider:
            spider.logger.warning(
                "Proxy pool size is %s; expected >= %s for stable rotation.",
                len(self.pool),
                MIN_PROXY_POOL_SIZE,
            )
            self._warned = True
        request.meta["proxy"] = random.choice(self.pool)


class ScrapeOpsProxyMiddleware:
    """Routes requests through ScrapeOps proxy aggregator when API key is present."""

    endpoint = "https://proxy.scrapeops.io/v1/"

    def __init__(self):
        self.api_key = SCRAPEOPS_API_KEY

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider=None):
        if not self.api_key:
            return
        if request.meta.get("skip_scrapeops"):
            return
        if request.meta.get("_scrapeops_wrapped"):
            return

        params = {
            "api_key": self.api_key,
            "url": request.url,
            "country": "in",
            "residential": "true",
            "keep_headers": "true",
        }
        request._set_url(f"{self.endpoint}?{urlencode(params)}")
        request.meta["_scrapeops_wrapped"] = True