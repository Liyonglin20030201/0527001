"""美团餐厅爬虫"""

from crawler.spiders.base_spider import BaseRestaurantSpider


class MeituanSpider(BaseRestaurantSpider):
    """美团平台爬虫

    字段映射说明:
    - poiName -> name
    - address -> address
    - phone -> phone
    - cateName -> category
    - avgPrice -> avg_price
    - avgScore -> overall_score
    """

    name = "meituan"
    platform_name = "meituan"
    allowed_domains = ["meituan.com"]

    def __init__(self, city="beijing", max_pages=10, use_mock=True, *args, **kwargs):
        super().__init__(city, max_pages, use_mock, *args, **kwargs)
        self.start_urls = [
            f"https://www.meituan.com/{city}/meishi"
        ]

    def parse(self, response):
        """解析美团餐厅列表页(实际爬取逻辑，需要有效cookie)"""
        restaurants = response.css("div.list-item a.title::attr(href)").getall()
        for url in restaurants:
            yield response.follow(url, callback=self.parse_restaurant)

    def parse_restaurant(self, response):
        """解析美团餐厅详情页"""
        item = self._to_restaurant_item({
            "name": response.css("h1.name::text").get("").strip(),
            "address": response.css("span.address::text").get("").strip(),
            "phone": response.css("span.phone::text").get("").strip(),
            "category": response.css("span.cate::text").getall(),
            "avg_price": response.css("span.price em::text").get("").strip(),
            "overall_score": response.css("span.score::text").get("").strip(),
            "url": response.url,
            "tags": response.css("div.tags span::text").getall(),
            "recommended_dishes": response.css("div.dishes a::text").getall(),
        })
        yield item
