"""所有平台爬虫的基类"""

import json
import os
import scrapy
from scrapy import Request
from crawler.items import RestaurantItem, ReviewItem


class BaseRestaurantSpider(scrapy.Spider):
    """餐厅爬虫基类

    子类需覆盖:
    - platform_name: 平台标识 (如 "meituan", "eleme")
    - start_urls: 起始URL列表
    - parse(): 解析逻辑
    """

    platform_name = ""
    allowed_domains = []

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "COOKIES_ENABLED": True,
        "RETRY_TIMES": 3,
    }

    def __init__(self, city="beijing", max_pages=10, use_mock=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.city = city
        self.max_pages = int(max_pages)
        self.use_mock = use_mock

    def start_requests(self):
        if self.use_mock:
            for item in self._load_mock_data():
                yield item
        else:
            for url in self.start_urls:
                yield Request(url, callback=self.parse)

    def _load_mock_data(self):
        """加载模拟数据"""
        base_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "mock"
        )

        restaurants_file = os.path.join(base_dir, f"{self.platform_name}_restaurants.jsonl")
        reviews_file = os.path.join(base_dir, f"{self.platform_name}_reviews.jsonl")

        if os.path.exists(restaurants_file):
            with open(restaurants_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        yield self._to_restaurant_item(data)

        if os.path.exists(reviews_file):
            with open(reviews_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        yield self._to_review_item(data)

    def _to_restaurant_item(self, data):
        """将原始字典转为 RestaurantItem"""
        item = RestaurantItem()
        item["name"] = data.get("name", "")
        item["address"] = data.get("address", "")
        item["phone"] = data.get("phone", "")
        item["category"] = data.get("category", [])
        item["avg_price"] = data.get("avg_price", "")
        item["overall_score"] = data.get("overall_score", "")
        item["url"] = data.get("url", "")
        item["tags"] = data.get("tags", [])
        item["recommended_dishes"] = data.get("recommended_dishes", [])
        item["source_platform"] = self.platform_name
        return item

    def _to_review_item(self, data):
        """将原始字典转为 ReviewItem"""
        item = ReviewItem()
        item["restaurant_name"] = data.get("restaurant_name", "")
        item["restaurant_url"] = data.get("restaurant_url", "")
        item["user"] = data.get("user", "")
        item["score"] = data.get("score", "")
        item["content"] = data.get("content", "")
        item["date"] = data.get("date", "")
        item["dishes_mentioned"] = data.get("dishes_mentioned", [])
        item["source_platform"] = self.platform_name
        return item
