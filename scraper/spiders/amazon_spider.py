import random
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

import scrapy
from parsel import Selector

from config.config import (
    DEFAULT_MARGIN_PCT,
    SEARCH_BRAND,
    SEARCH_PAGES,
    TARGET_ASINS,
    TARGET_MODELS,
    TN_PINCODES,
    YOUR_PRICE_BY_ASIN,
)
from scraper.items import AmazonProductItem
from scraper.selenium_helper import fetch_all_offers


class AmazonSpider(scrapy.Spider):
    name = "amazon"

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        settings = crawler.settings

        spider.target_asins = settings.getlist("TARGET_ASINS") or TARGET_ASINS
        spider.target_models = settings.getlist("TARGET_MODELS") or TARGET_MODELS
        spider.search_brand = settings.get("SEARCH_BRAND", SEARCH_BRAND)
        spider.search_pages = settings.getint("SEARCH_PAGES", SEARCH_PAGES)
        spider.default_margin_pct = settings.getfloat("DEFAULT_MARGIN_PCT", DEFAULT_MARGIN_PCT)
        spider.your_price_by_asin = settings.getdict("YOUR_PRICE_BY_ASIN") or YOUR_PRICE_BY_ASIN
        spider._seen_asins = set()
        return spider

    async def start(self):
        for request in self.start_requests():
            yield request

    def start_requests(self):
        if self.target_models:
            for model in self.target_models:
                keyword = f"{self.search_brand} bearing {model}"
                for page in range(1, self.search_pages + 1):
                    query = quote_plus(keyword)
                    url = f"https://www.amazon.in/s?k={query}&page={page}"
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse_search,
                        dont_filter=True,
                        meta={"model": model, "page": page, "search_keyword": keyword},
                    )
            return

        for asin in self.target_asins:
            yield scrapy.Request(
                url=f"https://www.amazon.in/dp/{asin}?aod=1",
                callback=self.parse_offer_page,
                meta={"asin": asin, "search_keyword": "direct_asin"},
                dont_filter=True,
            )

    def parse_search(self, response):
        model = response.meta.get("model", "")
        page = response.meta.get("page", 1)
        search_keyword = response.meta.get("search_keyword", "")
        cards = response.css("div.s-result-item[data-asin]")
        discovered = 0

        for card in cards:
            asin = (card.attrib.get("data-asin") or "").strip()
            if not asin or asin in self._seen_asins:
                continue

            product_name = card.css("h2 a span::text").get(default="").strip()
            category = card.css("span.a-size-base.a-color-secondary::text").get(default="").strip()

            self._seen_asins.add(asin)
            discovered += 1

            yield scrapy.Request(
                url=f"https://www.amazon.in/dp/{asin}?aod=1",
                callback=self.parse_offer_page,
                dont_filter=True,
                meta={
                    "asin": asin,
                    "model": model,
                    "source_page": page,
                    "search_keyword": search_keyword,
                    "product_name": product_name,
                    "category": category,
                },
            )

        self.logger.info(
            "Search model=%s page=%s discovered_asins=%s",
            model,
            page,
            discovered,
        )

    def parse_offer_page(self, response):
        asin = response.meta["asin"]
        pincode = random.choice(TN_PINCODES)
        proxy_url = response.meta.get("proxy")
        source_page = response.meta.get("source_page")
        search_keyword = response.meta.get("search_keyword", "")

        product_name = (response.meta.get("product_name") or "").strip()
        category = (response.meta.get("category") or "").strip()
        product_url = f"https://www.amazon.in/dp/{asin}"

        self.logger.info("Fetching all offers for ASIN %s via Selenium...", asin)

        html, pincode = fetch_all_offers(asin, pincode, proxy_url=proxy_url)
        sel = Selector(text=html)

        if not product_name:
            product_name = self._extract_product_name(response, sel)
        if not category:
            category = self._extract_category(response, sel)

        offer_items = []

        pinned = sel.css("#aod-pinned-offer")
        if pinned:
            item = self._extract_offer(
                offer=pinned[0],
                asin=asin,
                pincode=pincode,
                is_featured=1,
                product_name=product_name,
                category=category,
                product_url=product_url,
                search_keyword=search_keyword,
                source_page=source_page,
            )
            if item:
                offer_items.append(item)

        offers = sel.css("#aod-offer")
        self.logger.info("ASIN %s: found %s additional offers", asin, len(offers))

        for offer in offers:
            item = self._extract_offer(
                offer=offer,
                asin=asin,
                pincode=pincode,
                is_featured=0,
                product_name=product_name,
                category=category,
                product_url=product_url,
                search_keyword=search_keyword,
                source_page=source_page,
            )
            if item:
                offer_items.append(item)

        if not offer_items:
            self.logger.warning("No AOD offers found for %s, trying static fallback...", asin)
            offer_items.extend(
                self._parse_static_fallback(
                    sel=sel,
                    asin=asin,
                    pincode=pincode,
                    product_name=product_name,
                    category=category,
                    product_url=product_url,
                    search_keyword=search_keyword,
                    source_page=source_page,
                )
            )

        for item in offer_items:
            yield item

        snapshot = self._build_snapshot(
            asin=asin,
            pincode=pincode,
            product_name=product_name,
            category=category,
            product_url=product_url,
            search_keyword=search_keyword,
            source_page=source_page,
            offer_items=offer_items,
        )
        if snapshot:
            yield snapshot

    def _parse_static_fallback(
        self,
        sel,
        asin,
        pincode,
        product_name,
        category,
        product_url,
        search_keyword,
        source_page,
    ):
        items = []
        for link in sel.css("a[href*='seller=']"):
            seller_name = link.css("::text").get(default="").strip()
            seller_url = link.attrib.get("href", "")
            seller_id = ""
            if "seller=" in seller_url:
                seller_id = seller_url.split("seller=")[-1].split("&")[0]

            if not seller_name:
                continue

            price_text = self._extract_price_text(sel)
            if "%" in price_text:
                price_text = ""

            item = AmazonProductItem()
            item["item_type"] = "offer"
            item["asin"] = asin
            item["product_name"] = product_name
            item["category"] = category
            item["product_url"] = product_url
            item["search_keyword"] = search_keyword
            item["source_page"] = source_page or 0
            item["pincode"] = pincode
            item["seller_name"] = seller_name
            item["seller_id"] = seller_id
            item["price"] = price_text
            item["price_value"] = self._parse_price_value(price_text)
            item["shipping"] = ""
            item["fba_status"] = "FBA" if "amazon" in seller_name.lower() else "FBM"
            item["condition_type"] = "New"
            item["is_featured"] = 1
            item["seller_rating"] = ""
            item["scraped_at"] = self._utc_now_iso()
            items.append(item)

        return items

    def _extract_offer(
        self,
        offer,
        asin,
        pincode,
        is_featured,
        product_name,
        category,
        product_url,
        search_keyword,
        source_page,
    ):
        item = AmazonProductItem()
        item["item_type"] = "offer"
        item["asin"] = asin
        item["product_name"] = product_name
        item["category"] = category
        item["product_url"] = product_url
        item["search_keyword"] = search_keyword
        item["source_page"] = source_page or 0
        item["pincode"] = pincode
        item["is_featured"] = is_featured
        item["scraped_at"] = self._utc_now_iso()

        price = self._extract_price_text(offer)
        item["price"] = price
        item["price_value"] = self._parse_price_value(price)

        seller_name = ""
        for css_sel in [
            "#aod-offer-soldBy a",
            "a[href*='seller=']",
            ".aod-merchant-info a",
            "span.a-size-small a",
        ]:
            seller_name = offer.css(css_sel + "::text").get(default="").strip()
            if seller_name:
                break
        item["seller_name"] = seller_name

        seller_href = (
            offer.css("#aod-offer-soldBy a::attr(href)").get(default="")
            or offer.css("a[href*='seller=']::attr(href)").get(default="")
        )
        seller_id = ""
        if "seller=" in seller_href:
            seller_id = seller_href.split("seller=")[-1].split("&")[0]
        item["seller_id"] = seller_id

        ships_from = (
            offer.css("#aod-offer-shipsFrom span.a-color-base::text").get(default="")
            or offer.css("div[id*='shipsFrom'] span::text").get(default="")
        ).strip()
        item["shipping"] = "Free" if "free" in ships_from.lower() else ships_from

        item["fba_status"] = (
            "FBA"
            if "amazon" in ships_from.lower()
            else "FBA"
            if "amazon" in seller_name.lower()
            else "FBM"
        )

        item["seller_rating"] = (
            offer.css("span[id*='seller-rating']::text").get(default="")
            or offer.css("span[class*='seller-rating']::text").get(default="")
            or offer.css("i span.a-icon-alt::text").get(default="")
        ).strip()

        item["condition_type"] = "New"

        if not price and not seller_name:
            return None

        return item

    def _build_snapshot(
        self,
        asin,
        pincode,
        product_name,
        category,
        product_url,
        search_keyword,
        source_page,
        offer_items,
    ):
        if not offer_items:
            return None

        numeric_prices = [
            float(item.get("price_value"))
            for item in offer_items
            if item.get("price_value") is not None
        ]

        lowest_price = min(numeric_prices) if numeric_prices else None
        highest_price = max(numeric_prices) if numeric_prices else None
        average_price = (sum(numeric_prices) / len(numeric_prices)) if numeric_prices else None

        seller_keys = {
            (item.get("seller_id") or "", item.get("seller_name") or "")
            for item in offer_items
            if item.get("seller_name")
        }

        fba_sellers = {
            (item.get("seller_id") or "", item.get("seller_name") or "")
            for item in offer_items
            if (item.get("fba_status") or "").upper() == "FBA" and item.get("seller_name")
        }

        active_sellers = len(seller_keys)
        fba_count = len(fba_sellers)
        fbm_count = max(active_sellers - fba_count, 0)

        if lowest_price is not None:
            recommended_price = round(lowest_price * (1 + (self.default_margin_pct / 100.0)), 2)
        else:
            recommended_price = None

        your_price = self.your_price_by_asin.get(asin)
        if your_price is None and recommended_price is not None:
            your_price = recommended_price

        undercut_alert = bool(
            your_price is not None and lowest_price is not None and float(your_price) > float(lowest_price)
        )

        snapshot = AmazonProductItem()
        snapshot["item_type"] = "snapshot"
        snapshot["asin"] = asin
        snapshot["product_name"] = product_name
        snapshot["category"] = category
        snapshot["product_url"] = product_url
        snapshot["search_keyword"] = search_keyword
        snapshot["source_page"] = source_page or 0
        snapshot["pincode"] = pincode
        snapshot["lowest_price"] = lowest_price
        snapshot["highest_price"] = highest_price
        snapshot["average_price"] = round(average_price, 2) if average_price is not None else None
        snapshot["recommended_price"] = recommended_price
        snapshot["your_price"] = your_price
        snapshot["active_sellers"] = active_sellers
        snapshot["fba_sellers"] = fba_count
        snapshot["fbm_sellers"] = fbm_count
        snapshot["undercut_alert"] = 1 if undercut_alert else 0
        snapshot["trend_percent"] = None
        snapshot["scraped_at"] = self._utc_now_iso()

        return snapshot

    @staticmethod
    def _extract_product_name(response, sel):
        candidates = [
            response.css("#productTitle::text").get(default="").strip(),
        ]
        if sel is not None:
            candidates.extend(
                [
                    sel.css("#productTitle::text").get(default="").strip(),
                    sel.css("title::text").get(default="").strip(),
                ]
            )
        for candidate in candidates:
            if candidate:
                return candidate
        return ""

    @staticmethod
    def _extract_category(response, sel):
        category = ""
        for crumb in response.css("#wayfinding-breadcrumbs_feature_div ul li a::text").getall():
            crumb = crumb.strip()
            if crumb:
                category = crumb

        if not category and sel is not None:
            for crumb in sel.css("#wayfinding-breadcrumbs_feature_div ul li a::text").getall():
                crumb = crumb.strip()
                if crumb:
                    category = crumb

        return category

    @staticmethod
    def _parse_price_value(price_text):
        if not price_text:
            return None
        if "%" in price_text:
            return None
        match = re.search(r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)", price_text)
        if not match:
            return None
        cleaned = match.group(1).replace(",", "")

        try:
            return round(float(cleaned), 2)
        except ValueError:
            return None

    @staticmethod
    def _extract_price_text(node):
        selectors = [
            "span.a-price span.a-offscreen::text",
            "span[class*='price'] span.a-offscreen::text",
            ".aod-price span.a-offscreen::text",
            "span.a-color-price::text",
        ]
        for css_sel in selectors:
            value = node.css(css_sel).get(default="").strip()
            normalized = AmazonSpider._normalize_price_candidate(value)
            if normalized:
                return normalized

        # Some offers render split price parts instead of a-offscreen.
        whole = node.css("span.a-price-whole::text").get(default="").strip().replace(",", "")
        frac = node.css("span.a-price-fraction::text").get(default="").strip()
        if whole.isdigit() and frac.isdigit():
            return f"{whole}.{frac}"
        if whole.isdigit():
            return whole

        # Final fallback: scan text for the first numeric token that looks like a price.
        for text in node.css("::text").getall():
            value = text.strip()
            normalized = AmazonSpider._normalize_price_candidate(value)
            if normalized:
                return normalized

        return ""

    @staticmethod
    def _normalize_price_candidate(value):
        if not value:
            return ""
        compact = " ".join(value.split())
        if "%" in compact:
            return ""

        match = re.search(r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)", compact)
        if not match:
            return ""

        token = match.group(1)
        digits = token.replace(",", "").replace(".", "")
        if len(digits) < 3:
            return ""
        return token

    @staticmethod
    def _utc_now_iso():
        return datetime.now(timezone.utc).isoformat()
