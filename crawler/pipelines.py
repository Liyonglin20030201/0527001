import json
import os


class JsonPipeline:
    """将爬取数据保存为JSON文件"""

    def open_spider(self, spider):
        output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(output_dir, exist_ok=True)
        self.restaurant_file = open(
            os.path.join(output_dir, "restaurants.jsonl"), "a", encoding="utf-8"
        )
        self.review_file = open(
            os.path.join(output_dir, "reviews.jsonl"), "a", encoding="utf-8"
        )

    def close_spider(self, spider):
        self.restaurant_file.close()
        self.review_file.close()

    def process_item(self, item, spider):
        from crawler.items import RestaurantItem, ReviewItem

        data = dict(item)
        if isinstance(item, RestaurantItem):
            self.restaurant_file.write(json.dumps(data, ensure_ascii=False) + "\n")
        elif isinstance(item, ReviewItem):
            self.review_file.write(json.dumps(data, ensure_ascii=False) + "\n")
        return item
