import scrapy

class DebugSpider(scrapy.Spider):
    name = "debug"
    allowed_domains = ["amazon.in"]

    def start_requests(self):
        asin = "B07H1GJZMP"
        yield scrapy.Request(
            f"https://www.amazon.in/dp/{asin}?aod=1&condition=new",
            callback=self.parse,
            headers={
                "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-IN,en;q=0.9",
                "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Referer":         "https://www.amazon.in",
            },
            dont_filter=True,
        )

    def parse(self, response):
        with open("debug_output.html", "wb") as f:
            f.write(response.body)

        self.logger.info("── SELLER LINKS FOUND ──")
        sellers = response.css("a[href*='seller=']")
        self.logger.info(f"Total seller links: {len(sellers)}")

        for i, link in enumerate(sellers):
            href      = link.attrib.get("href", "")
            name      = link.css("::text").get(default="").strip()
            seller_id = href.split("seller=")[-1].split("&")[0] if "seller=" in href else ""
            self.logger.info(f"  [{i}] name='{name}' | id='{seller_id}'")

        self.logger.info("── PRICES FOUND ──")
        prices = response.css("span.a-price span.a-offscreen")
        self.logger.info(f"Total prices: {len(prices)}")
        for i, p in enumerate(prices):
            self.logger.info(f"  [{i}] {p.css('::text').get()}")

        self.logger.info("── OFFER CONTAINERS ──")

        # Based on the HTML we saw — offer-display-feature-text is the container
        offer_rows = response.css("div[id^='offer-display-features-']")
        self.logger.info(f"offer-display-features-* divs: {len(offer_rows)}")

        # Each offer row
        for i, row in enumerate(offer_rows):
            seller = row.css("a[href*='seller=']::text").get(default="").strip()
            s_href = row.css("a[href*='seller=']::attr(href)").get(default="")
            s_id   = s_href.split("seller=")[-1].split("&")[0] if "seller=" in s_href else ""
            price  = row.css("span.a-price span.a-offscreen::text").get(default="").strip()
            self.logger.info(f"  ROW [{i}] seller='{seller}' | id='{s_id}' | price='{price}'")

        # Also try the offer-display-feature-text-message span
        self.logger.info("── offer-display-feature-text-message ──")
        msgs = response.css("span.offer-display-feature-text-message")
        self.logger.info(f"Total: {len(msgs)}")
        for i, m in enumerate(msgs):
            self.logger.info(f"  [{i}] text='{m.css('::text').get(default='').strip()}' | link='{m.css('a::text').get(default='').strip()}'")

        # Try tabular buybox rows
        self.logger.info("── tabular-buybox rows ──")
        rows = response.css("div.tabular-buybox-container, div#tabular-buybox")
        self.logger.info(f"Total: {len(rows)}")
        for i, row in enumerate(rows):
            self.logger.info(f"  [{i}] {row.get()[:300]}")