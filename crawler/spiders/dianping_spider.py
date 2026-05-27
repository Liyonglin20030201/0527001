import scrapy
from scrapy import Request
from crawler.items import RestaurantItem, ReviewItem


class DianpingSpider(scrapy.Spider):
    """大众点评餐厅爬虫

    采集策略：
    1. 从城市美食列表页获取餐厅基本信息
    2. 进入餐厅详情页获取菜品和评论
    3. 翻页采集所有评论
    """

    name = "dianping"
    allowed_domains = ["dianping.com"]
    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "COOKIES_ENABLED": True,
        "RETRY_TIMES": 3,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    }

    def __init__(self, city="beijing", max_pages=10, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.city = city
        self.max_pages = int(max_pages)
        self.start_urls = [
            f"https://www.dianping.com/{city}/ch10"
        ]

    def parse(self, response):
        """解析餐厅列表页"""
        restaurants = response.css("div.txt a.tit::attr(href)").getall()
        for url in restaurants:
            yield Request(
                response.urljoin(url),
                callback=self.parse_restaurant,
            )

        current_page = response.css("span.PageLink .current::text").get()
        if current_page and int(current_page) < self.max_pages:
            next_page = response.css("a.NextPage::attr(href)").get()
            if next_page:
                yield Request(response.urljoin(next_page), callback=self.parse)

    def parse_restaurant(self, response):
        """解析餐厅详情页"""
        item = RestaurantItem()
        item["name"] = response.css("h1.shop-name::text").get("").strip()
        item["address"] = response.css("span.item::text").get("").strip()
        item["phone"] = response.css("p.tel::text").get("").strip()
        item["category"] = response.css("a.breadcrumb-link::text").getall()
        item["avg_price"] = response.css("span.avgPriceTitle::text").get("").strip()
        item["overall_score"] = response.css("span.mid-score::text").get("").strip()
        item["url"] = response.url

        tags = response.css("div.shop-tag span::text").getall()
        item["tags"] = [t.strip() for t in tags if t.strip()]

        dishes = []
        for dish in response.css("div.recommend-dishes a"):
            dish_name = dish.css("::text").get("").strip()
            if dish_name:
                dishes.append(dish_name)
        item["recommended_dishes"] = dishes

        yield item

        review_url = response.url.rstrip("/") + "/review_all"
        yield Request(
            review_url,
            callback=self.parse_reviews,
            meta={"restaurant_name": item["name"], "restaurant_url": response.url},
        )

    def parse_reviews(self, response):
        """解析评论页"""
        restaurant_name = response.meta["restaurant_name"]
        restaurant_url = response.meta["restaurant_url"]

        for review in response.css("div.review-list-item"):
            item = ReviewItem()
            item["restaurant_name"] = restaurant_name
            item["restaurant_url"] = restaurant_url
            item["user"] = review.css("a.name::text").get("").strip()
            item["score"] = review.css("span.score span::attr(class)").get("")
            item["content"] = review.css("div.review-words::text").get("").strip()
            item["date"] = review.css("span.time::text").get("").strip()

            dishes_mentioned = review.css("span.dishes-mention::text").getall()
            item["dishes_mentioned"] = [d.strip() for d in dishes_mentioned]

            yield item

        next_page = response.css("a.NextPage::attr(href)").get()
        if next_page:
            yield Request(
                response.urljoin(next_page),
                callback=self.parse_reviews,
                meta=response.meta,
            )
