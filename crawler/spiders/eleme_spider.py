"""饿了么餐厅爬虫"""

from crawler.spiders.base_spider import BaseRestaurantSpider


class ElemeSpider(BaseRestaurantSpider):
    """饿了么平台爬虫

    字段映射说明:
    - restaurant_name -> name
    - address -> address
    - phone -> phone
    - category -> category (饿了么分类粒度较粗)
    - average_cost -> avg_price
    - rating -> overall_score (饿了么满分5分)
    """

    name = "eleme"
    platform_name = "eleme"
    allowed_domains = ["ele.me"]

    def __init__(self, city="beijing", max_pages=10, use_mock=True, *args, **kwargs):
        super().__init__(city, max_pages, use_mock, *args, **kwargs)
        self.start_urls = [
            f"https://www.ele.me/place/{city}"
        ]

    def parse(self, response):
        """解析饿了么餐厅列表页(实际爬取逻辑，需要有效认证)"""
        restaurants = response.css("a.restaurant-link::attr(href)").getall()
        for url in restaurants:
            yield response.follow(url, callback=self.parse_restaurant)

    def parse_restaurant(self, response):
        """解析饿了么餐厅详情页"""
        score_raw = response.css("span.rating::text").get("0").strip()
        try:
            score_normalized = str(round(float(score_raw) * 2, 1))
        except ValueError:
            score_normalized = ""

        item = self._to_restaurant_item({
            "name": response.css("h1.restaurant-name::text").get("").strip(),
            "address": response.css("p.address::text").get("").strip(),
            "phone": response.css("p.phone::text").get("").strip(),
            "category": response.css("span.category::text").getall(),
            "avg_price": response.css("span.avg-cost::text").get("").strip(),
            "overall_score": score_normalized,
            "url": response.url,
            "tags": response.css("div.tag-list span::text").getall(),
            "recommended_dishes": response.css("div.popular-food span.name::text").getall(),
        })
        yield item
