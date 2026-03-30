import mysql.connector

from config.config import DB_CONFIG


class MySQLPipeline:
    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def open_spider(self, spider=None):
        self.conn = mysql.connector.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()
        self._ensure_schema()

    def close_spider(self, spider=None):
        self.conn.commit()
        self.conn.close()

    def process_item(self, item, spider=None):
        item_type = (item.get("item_type") or "offer").lower()

        if item_type == "snapshot":
            self._insert_snapshot(item)
        else:
            self._insert_offer(item)

        self.conn.commit()
        return item

    def _ensure_schema(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS offer_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                asin VARCHAR(32) NOT NULL,
                product_name TEXT,
                category VARCHAR(255),
                product_url TEXT,
                search_keyword VARCHAR(255),
                source_page INT DEFAULT 0,
                pincode VARCHAR(16),
                seller_name VARCHAR(255),
                seller_id VARCHAR(64),
                seller_rating VARCHAR(64),
                price_text VARCHAR(64),
                price_value DECIMAL(10,2) NULL,
                shipping VARCHAR(128),
                fba_status VARCHAR(16),
                condition_type VARCHAR(64),
                is_featured TINYINT(1) DEFAULT 0,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_offer_asin_time (asin, scraped_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS asin_snapshots (
                id INT AUTO_INCREMENT PRIMARY KEY,
                asin VARCHAR(32) NOT NULL,
                product_name TEXT,
                category VARCHAR(255),
                product_url TEXT,
                search_keyword VARCHAR(255),
                source_page INT DEFAULT 0,
                pincode VARCHAR(16),
                lowest_price DECIMAL(10,2) NULL,
                highest_price DECIMAL(10,2) NULL,
                average_price DECIMAL(10,2) NULL,
                recommended_price DECIMAL(10,2) NULL,
                your_price DECIMAL(10,2) NULL,
                active_sellers INT DEFAULT 0,
                fba_sellers INT DEFAULT 0,
                fbm_sellers INT DEFAULT 0,
                undercut_alert TINYINT(1) DEFAULT 0,
                trend_percent DECIMAL(7,2) NULL,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_snapshot_asin_time (asin, scraped_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )


    def _insert_offer(self, item):
        sql = """
            INSERT INTO offer_records
                (asin, product_name, category, product_url, search_keyword, source_page,
                 pincode, seller_name, seller_id, seller_rating, price_text, price_value,
                 shipping, fba_status, condition_type, is_featured)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            item.get("asin", ""),
            item.get("product_name", ""),
            item.get("category", ""),
            item.get("product_url", ""),
            item.get("search_keyword", ""),
            int(item.get("source_page", 0) or 0),
            item.get("pincode", ""),
            item.get("seller_name", ""),
            item.get("seller_id", ""),
            item.get("seller_rating", ""),
            item.get("price", ""),
            item.get("price_value"),
            item.get("shipping", ""),
            item.get("fba_status", ""),
            item.get("condition_type", "New"),
            int(item.get("is_featured", 0) or 0),
        )
        self.cursor.execute(sql, values)

    def _insert_snapshot(self, item):
        asin = item.get("asin", "")
        trend_percent = item.get("trend_percent")

        if trend_percent is None:
            trend_percent = self._compute_trend_percent(asin, item.get("lowest_price"))

        sql = """
            INSERT INTO asin_snapshots
                (asin, product_name, category, product_url, search_keyword, source_page,
                 pincode, lowest_price, highest_price, average_price, recommended_price,
                 your_price, active_sellers, fba_sellers, fbm_sellers, undercut_alert,
                 trend_percent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            asin,
            item.get("product_name", ""),
            item.get("category", ""),
            item.get("product_url", ""),
            item.get("search_keyword", ""),
            int(item.get("source_page", 0) or 0),
            item.get("pincode", ""),
            item.get("lowest_price"),
            item.get("highest_price"),
            item.get("average_price"),
            item.get("recommended_price"),
            item.get("your_price"),
            int(item.get("active_sellers", 0) or 0),
            int(item.get("fba_sellers", 0) or 0),
            int(item.get("fbm_sellers", 0) or 0),
            int(item.get("undercut_alert", 0) or 0),
            trend_percent,
        )
        self.cursor.execute(sql, values)

    def _compute_trend_percent(self, asin, latest_lowest_price):
        if latest_lowest_price is None:
            return None

        self.cursor.execute(
            """
            SELECT lowest_price
            FROM asin_snapshots
            WHERE asin = %s AND lowest_price IS NOT NULL
            ORDER BY scraped_at DESC
            LIMIT 1
            """,
            (asin,),
        )
        row = self.cursor.fetchone()
        if not row:
            return 0.0

        previous_lowest = row[0]
        if previous_lowest is None or float(previous_lowest) == 0.0:
            return 0.0

        return round(((float(latest_lowest_price) - float(previous_lowest)) / float(previous_lowest)) * 100.0, 2)
