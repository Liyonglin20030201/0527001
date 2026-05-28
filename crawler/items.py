import scrapy


class RestaurantItem(scrapy.Item):
    """餐厅数据项"""
    name = scrapy.Field()
    address = scrapy.Field()
    phone = scrapy.Field()
    category = scrapy.Field()
    avg_price = scrapy.Field()
    overall_score = scrapy.Field()
    url = scrapy.Field()
    tags = scrapy.Field()
    recommended_dishes = scrapy.Field()
    source_platform = scrapy.Field()


class ReviewItem(scrapy.Item):
    """评论数据项"""
    restaurant_name = scrapy.Field()
    restaurant_url = scrapy.Field()
    user = scrapy.Field()
    score = scrapy.Field()
    content = scrapy.Field()
    date = scrapy.Field()
    dishes_mentioned = scrapy.Field()
    source_platform = scrapy.Field()
