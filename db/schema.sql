USE amazon_monitor;

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
);

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
);

-- Backwards-compatible table for older queries
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asin VARCHAR(32),
    title TEXT,
    price VARCHAR(64),
    seller_name VARCHAR(255),
    rating VARCHAR(64),
    num_reviews VARCHAR(32),
    url TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_products_asin_time (asin, scraped_at)
);
