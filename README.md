# Amazon Price Monitor (Bearing Distributors - Amazon India)

A Python-based scraping pipeline for monitoring bearing prices on Amazon India.

This project searches product listings (for example, SKF bearing models), discovers ASINs, fetches seller offers, and stores both raw offer-level records and analytics snapshots in MySQL.

## 1. Project Goal

Build a repeatable data pipeline that helps distributors answer:

- Which sellers are listing the same bearing ASIN?
- What are their latest prices?
- How is the lowest market price trending over time?
- Is your configured target price being undercut?

## 2. High-Level Architecture

1. Scrapy spider searches Amazon results pages using model-based queries.
2. Spider extracts ASINs from search results.
3. For each ASIN, Selenium renders the dynamic offer view (AOD / all offers).
4. Parsed offer data is emitted as Scrapy items.
5. Pipeline writes rows to MySQL tables:
   - `offer_records` (raw seller offers)
   - `asin_snapshots` (aggregated price intelligence)
6. Optional scheduler runs the scraper at intervals.

## 3. Tech Stack

- Python 3.12+
- Scrapy
- Selenium + webdriver-manager
- Parsel / lxml / cssselect
- MySQL (mysql-connector-python)
- APScheduler
- fake-useragent
- Optional ScrapeOps proxy integration

## 4. Repository Structure

- `run.py`: Main entrypoint (run scraper, cron mode, report mode)
- `config/config.py`: Runtime configuration and environment overrides
- `scraper/settings.py`: Scrapy settings and middleware pipeline
- `scraper/spiders/amazon_spider.py`: Main spider logic
- `scraper/spiders/debug_spider.py`: Debug spider for selector inspection
- `scraper/selenium_helper.py`: Selenium rendering and offer-page capture
- `scraper/middlewares.py`: User-agent, geo headers, proxy middlewares
- `scraper/pipelines.py`: MySQL insertion pipeline
- `scraper/items.py`: Item schema
- `db/schema.sql`: Database table definitions
- `requirements.txt`: Python dependencies

## 5. Data Collected

### 5.1 Offer-Level (`offer_records`)

Each row typically represents one seller offer observation:

- Product identity: `asin`, `product_name`, `category`, `product_url`
- Search context: `search_keyword`, `source_page`
- Location simulation: `pincode`
- Seller info: `seller_name`, `seller_id`, `seller_rating`
- Offer details: `price_text`, `price_value`, `shipping`, `fba_status`, `condition_type`
- Position hint: `is_featured` (pinned/default-like offer marker)
- Timestamp: `scraped_at`

### 5.2 Snapshot-Level (`asin_snapshots`)

Aggregated view per ASIN scrape event:

- `lowest_price`, `highest_price`, `average_price`
- `recommended_price` (based on configured margin)
- `your_price` (configured by ASIN)
- `active_sellers`, `fba_sellers`, `fbm_sellers`
- `undercut_alert`
- `trend_percent`
- context and timestamp fields (`asin`, `product_name`, etc.)

## 6. Prerequisites

- Windows/macOS/Linux
- Python 3.12+ installed
- MySQL server running
- Chrome installed (for Selenium ChromeDriver)

## 7. Setup

### 7.1 Create and activate virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 7.2 Install dependencies

```powershell
pip install -r requirements.txt
```

### 7.3 Create database

1. Create DB:

```sql
CREATE DATABASE amazon_monitor;
```

2. Apply schema:

```powershell
mysql -u root -p amazon_monitor < db/schema.sql
```

Note: The pipeline also creates core tables automatically if missing.

## 8. Configuration

Configuration is defined in `config/config.py` and can be overridden via environment variables.

Notes:

- `.env` is optional. You can run this project using values directly in `config/config.py`.
- If a `.env` file is present, values are auto-loaded via `python-dotenv`.

### 8.1 Database

- `DB_HOST` (default: `localhost`)
- `DB_USER` (default: `root`)
- `DB_PASSWORD` (default: `root123`)
- `DB_NAME` (default: `amazon_monitor`)

### 8.2 Crawl scope

- `TARGET_ASINS` (comma-separated)
- `TARGET_MODELS` (comma-separated)
- `SEARCH_BRAND` (default: `SKF`)
- `SEARCH_PAGES` (int)

### 8.3 Pricing strategy

- `DEFAULT_MARGIN_PCT` (float)
- `YOUR_PRICE_BY_ASIN_JSON` (JSON map)
  - Example: `{"B07H1GJZMP": 2249.0, "B07H88MND1": 1899.0}`

### 8.4 Proxy and geo

- `SCRAPEOPS_API_KEY`
- `PROXY_POOL` (comma-separated proxy URLs)
- `MIN_PROXY_POOL_SIZE` (default: `100`)
- `TN_PINCODES` (comma-separated Tamil Nadu pincodes)

## 9. Running the Project

### 9.1 Run scraper (default amazon mode)

```powershell
python run.py amazon
```

### 9.2 Run with custom target models and pages

```powershell
python run.py amazon --models 6206,6302 --search-pages 2
```

### 9.3 Run with explicit ASIN list

```powershell
python run.py amazon --asins B07H1GJZMP,B07H88MND1
```

### 9.4 Debug mode

```powershell
python run.py debug
```

This writes `debug_output.html` for selector troubleshooting.

### 9.5 Report mode (quick DB health check)

```powershell
python run.py report --limit 10
```

### 9.6 Scheduled mode (cron expression)

```powershell
python run.py cron --cron-expr "*/30 * * * *" --scheduled-mode amazon
```

## 10. Typical Validation Workflow

1. Run report and note counts.
2. Run a small scrape, for example one model and one page.
3. Run report again and confirm counts increased.
4. Inspect latest rows and generated Selenium HTML files.

## 11. Output Artifacts

- `selenium_output_<ASIN>.html`: Rendered offer page snapshots used for debugging and parser verification.
- `debug_output.html`: Raw debug response output from debug spider.

## 12. Anti-Blocking Strategy (Current)

- Random user-agent rotation
- Geo-flavored headers and rotating TN pincodes
- Optional raw proxy rotation
- Optional ScrapeOps proxy wrapping
- Selenium retry behavior for empty/captcha-like responses

## 13. Known Limitations

- Amazon anti-bot mechanisms can still reduce seller visibility.
- Some ASIN pages may expose only pinned/default-like offer depending on location/session.
- Buy Box/default seller detection is inferred from page structure and may need periodic selector updates.
- A duplicate legacy spider exists under `scraper/scraper/spiders/amazon_spider.py` and is not the primary execution path.

## 14. Troubleshooting

### 14.1 No new rows in DB

- Check DB credentials (`DB_*` env vars)
- Run `python run.py report --limit 3`
- Verify MySQL service is running

### 14.2 Selenium failures

- Ensure Chrome is installed
- Re-run after webdriver-manager downloads matching driver
- Check network/proxy availability

### 14.3 Empty offer lists

- Try different models/ASINs
- Validate generated `selenium_output_<ASIN>.html`
- Increase proxy quality or rotate location signals

## 15. Suggested Next Steps

- Add structured metrics and run logs to file
- Add stronger Buy Box/default-seller extraction logic
- Add alerting for significant price drops
- Build dashboard on top of `asin_snapshots`

## 16. Disclaimer

Use this project responsibly and ensure your usage complies with Amazon policies, applicable laws, and your organization's compliance requirements.

## 17. Sharing on GitHub (Local MySQL)

You can share this project as a public/private GitHub repository even if your MySQL runs locally.

1. Keep machine-specific DB credentials local (do not commit real secrets).
2. Keep schema in version control (`db/schema.sql`) so others can reproduce DB setup.
3. Ensure `.gitignore` excludes local artifacts such as `venv/`, debug HTML, and `.env`.
4. Mention in setup instructions that users must run MySQL locally (or provide their own DB host).
