BOT_NAME = "restaurant_crawler"

SPIDER_MODULES = ["crawler.spiders"]
NEWSPIDER_MODULE = "crawler.spiders"

ROBOTSTXT_OBEY = False

DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 1

COOKIES_ENABLED = True

ITEM_PIPELINES = {
    "crawler.pipelines.JsonPipeline": 300,
}

DOWNLOADER_MIDDLEWARES = {
    "crawler.middlewares.RandomUserAgentMiddleware": 400,
}

LOG_LEVEL = "INFO"
