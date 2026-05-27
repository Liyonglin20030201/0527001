"""运行Scrapy爬虫的入口脚本"""

import sys
import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

sys.path.insert(0, os.path.dirname(__file__))

from config import Config


def main():
    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "crawler.settings")
    settings = get_project_settings()
    process = CrawlerProcess(settings)

    process.crawl(
        "dianping",
        city=Config.SCRAPY_CITY,
        max_pages=Config.SCRAPY_MAX_PAGES,
    )
    process.start()


if __name__ == "__main__":
    main()
