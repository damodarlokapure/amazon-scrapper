import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SCRAPY_SETTINGS_MODULE"] = "scraper.settings"

import mysql.connector
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from config.config import DB_CONFIG
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scraper.spiders.amazon_spider import AmazonSpider
from scraper.spiders.debug_spider import DebugSpider

def _parse_cli():
    parser = argparse.ArgumentParser(description="Amazon price monitor runner")
    parser.add_argument("mode", nargs="?", default="amazon", choices=["amazon", "debug", "cron", "report"], help="Run mode")
    parser.add_argument("extra", nargs="*", help="Backward-compatible extra args (url for amazon, cron expr + mode for cron, limit for report)")

    parser.add_argument("--asins", dest="asins", help="Comma-separated ASINs to override target list")
    parser.add_argument("--models", dest="models", help="Comma-separated bearing models to search (e.g., 6206,6302)")
    parser.add_argument("--margin", dest="margin", type=float, help="Default margin percent for recommended price")
    parser.add_argument("--search-pages", dest="search_pages", type=int, help="Number of search result pages to crawl")
    parser.add_argument("--url", dest="url", help="Direct URL for amazon mode (optional)")
    parser.add_argument("--limit", dest="limit", type=int, help="Rows to show for report mode")
    parser.add_argument("--cron-expr", dest="cron_expr", help="Cron expression for cron mode", default="*/30 * * * *")
    parser.add_argument("--scheduled-mode", dest="scheduled_mode", help="Mode to run within cron", default="amazon")
    return parser.parse_args()


def _apply_overrides(settings, args):
    if args.asins:
        settings.set("TARGET_ASINS", [p.strip() for p in args.asins.split(",") if p.strip()], priority="cmdline")
    if args.models:
        settings.set("TARGET_MODELS", [p.strip() for p in args.models.split(",") if p.strip()], priority="cmdline")
    if args.margin is not None:
        settings.set("DEFAULT_MARGIN_PCT", float(args.margin), priority="cmdline")
    if args.search_pages is not None:
        settings.set("SEARCH_PAGES", int(args.search_pages), priority="cmdline")


def run_spider(args):
    settings = get_project_settings()
    _apply_overrides(settings, args)

    process = CrawlerProcess(settings)

    if args.mode == "debug":
        process.crawl(DebugSpider)
    else:
        kwargs = {"url": args.url} if args.url else {}
        process.crawl(AmazonSpider, **kwargs)

    process.start()


def run_cron(cron_expr="*/30 * * * *", mode="amazon"):
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    def _job():
        subprocess.run([sys.executable, os.path.abspath(__file__), mode], check=False)

    scheduler.add_job(_job, CronTrigger.from_crontab(cron_expr))
    print(f"[Cron] Scheduled mode={mode} with '{cron_expr}'")
    scheduler.start()


def print_report(limit=10):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM offer_records")
        offers_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM asin_snapshots")
        snapshots_count = cursor.fetchone()[0]

        print("\n=== Scraper Output Report ===")
        print(f"offer_records count   : {offers_count}")
        print(f"asin_snapshots count : {snapshots_count}")

        cursor.execute(
            """
            SELECT asin, product_name, seller_name, price_text, price_value, fba_status, pincode, scraped_at
            FROM offer_records
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )
        offer_rows = cursor.fetchall()

        print(f"\nLatest {limit} offer rows:")
        if not offer_rows:
            print("No offer rows found.")
        else:
            for row in offer_rows:
                asin, product_name, seller_name, price_text, price_value, fba_status, pincode, scraped_at = row
                title = (product_name or "")[:48]
                print(
                    f"ASIN={asin} | Seller={seller_name or '-'} | Price={price_text or '-'} ({price_value}) "
                    f"| FBA={fba_status or '-'} | PIN={pincode or '-'} | {title} | {scraped_at}"
                )

        cursor.execute(
            """
            SELECT asin, product_name, lowest_price, recommended_price, your_price,
                   active_sellers, undercut_alert, trend_percent, scraped_at
            FROM asin_snapshots
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )
        snapshot_rows = cursor.fetchall()

        print(f"\nLatest {limit} snapshot rows:")
        if not snapshot_rows:
            print("No snapshot rows found.")
        else:
            for row in snapshot_rows:
                asin, product_name, lowest_price, recommended_price, your_price, active_sellers, undercut_alert, trend_percent, scraped_at = row
                title = (product_name or "")[:48]
                print(
                    f"ASIN={asin} | Low={lowest_price} | Rec={recommended_price} | Yours={your_price} "
                    f"| Sellers={active_sellers} | Alert={undercut_alert} | Trend={trend_percent} "
                    f"| {title} | {scraped_at}"
                )

        print("\nDone.")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    args = _parse_cli()

    if args.mode == "cron":
        # Backward-compatible positional extra: cron_expr, scheduled_mode
        cron_expr = args.cron_expr
        scheduled_mode = args.scheduled_mode
        if args.extra:
            if len(args.extra) >= 1:
                cron_expr = args.extra[0]
            if len(args.extra) >= 2:
                scheduled_mode = args.extra[1]
        run_cron(cron_expr, scheduled_mode)
    elif args.mode == "report":
        limit = args.limit if args.limit is not None else 10
        if args.extra:
            try:
                limit = int(args.extra[0])
            except ValueError:
                pass
        print_report(limit=limit)
    else:
        # amazon or debug
        if args.mode == "amazon" and args.extra:
            # Backward-compatible url positional
            args.url = args.extra[0]
        run_spider(args)