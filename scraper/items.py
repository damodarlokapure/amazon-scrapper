# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class AmazonProductItem(scrapy.Item):
    item_type = scrapy.Field()  # offer | snapshot

    # Shared / identity fields
    asin = scrapy.Field()
    product_name = scrapy.Field()
    category = scrapy.Field()
    product_url = scrapy.Field()
    pincode = scrapy.Field()
    search_keyword = scrapy.Field()
    source_page = scrapy.Field()
    scraped_at = scrapy.Field()

    # Offer-level fields
    seller_name = scrapy.Field()
    seller_id = scrapy.Field()
    seller_rating = scrapy.Field()
    price = scrapy.Field()
    price_value = scrapy.Field()
    shipping = scrapy.Field()
    fba_status = scrapy.Field()
    condition_type = scrapy.Field()
    is_featured = scrapy.Field()

    # Snapshot-level fields (for dashboard/table views)
    lowest_price = scrapy.Field()
    highest_price = scrapy.Field()
    average_price = scrapy.Field()
    recommended_price = scrapy.Field()
    your_price = scrapy.Field()
    active_sellers = scrapy.Field()
    fba_sellers = scrapy.Field()
    fbm_sellers = scrapy.Field()
    undercut_alert = scrapy.Field()
    trend_percent = scrapy.Field()