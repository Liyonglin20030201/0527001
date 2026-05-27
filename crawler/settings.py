BOT_NAME = "restaurant_crawler"

SPIDER_MODULES = ["crawler.spiders"]
NEWSPIDER_MODULE = "crawler.spiders"

# 遵守 robots.txt（大众点评需关闭才能爬取）
ROBOTSTXT_OBEY = False

# 并发与延迟控制
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 30

# Cookies
COOKIES_ENABLED = True
COOKIES_DEBUG = False

# 重试
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# 请求头
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

# 下载中间件
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "crawler.middlewares.RandomUserAgentMiddleware": 400,
}

# Item Pipeline
ITEM_PIPELINES = {
    "crawler.pipelines.JsonPipeline": 300,
}

# 输出编码
FEED_EXPORT_ENCODING = "utf-8"

# 日志
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

# 缓存（开发时启用可加速调试）
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 86400
HTTPCACHE_DIR = ".scrapy_cache"

# AutoThrottle 自适应限速
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3
AUTOTHROTTLE_MAX_DELAY = 15
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
