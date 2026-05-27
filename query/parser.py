"""自然语言查询解析模块"""

import jieba
import re


FLAVOR_MAPPING = {
    "辣": ["辣", "麻辣", "香辣", "微辣", "特辣"],
    "清淡": ["清淡", "少油", "养生", "素"],
    "甜": ["甜", "甜品", "甜食"],
    "鲜": ["鲜", "海鲜", "新鲜"],
    "酸": ["酸", "酸辣"],
}

ATMOSPHERE_MAPPING = {
    "安静": ["安静", "静", "清静", "幽静", "不吵"],
    "浪漫": ["浪漫", "情侣", "约会", "情调"],
    "家庭": ["家庭", "亲子", "带孩子", "全家"],
    "商务": ["商务", "宴请", "请客", "接待"],
    "热闹": ["热闹", "聚餐", "聚会", "朋友"],
    "文艺": ["文艺", "小资", "网红", "打卡"],
}

PRICE_PATTERNS = [
    (r"(\d+)\s*[元块]?以[下内]", lambda m: (0, int(m.group(1)))),
    (r"(\d+)\s*[元块]?以上", lambda m: (int(m.group(1)), 9999)),
    (r"(\d+)\s*[-~到至]\s*(\d+)", lambda m: (int(m.group(1)), int(m.group(2)))),
    (r"便宜|实惠|性价比", lambda m: (0, 80)),
    (r"中等|适中", lambda m: (80, 200)),
    (r"高档|贵|奢华", lambda m: (200, 9999)),
]

CATEGORY_KEYWORDS = {
    "火锅": ["火锅", "涮锅", "涮肉"],
    "日料": ["日料", "日本料理", "寿司", "刺身", "拉面"],
    "川菜": ["川菜", "四川", "成都"],
    "粤菜": ["粤菜", "广东菜", "早茶", "港式"],
    "西餐": ["西餐", "牛排", "意面", "披萨"],
    "烧烤": ["烧烤", "烤肉", "撸串"],
    "韩餐": ["韩餐", "韩国料理", "烤肉", "部队锅"],
    "湘菜": ["湘菜", "湖南菜"],
    "东北菜": ["东北菜", "东北", "铁锅炖"],
    "咖啡": ["咖啡", "咖啡厅", "café"],
    "甜品": ["甜品", "蛋糕", "下午茶"],
}


class QueryParser:
    """自然语言查询解析器

    将用户的自由文本转换为结构化查询条件:
    - 口味偏好 (辣、清淡、鲜...)
    - 氛围要求 (安静、浪漫、热闹...)
    - 价格范围
    - 菜系类别
    - 具体菜品
    - 地理位置
    """

    def __init__(self):
        for keywords in FLAVOR_MAPPING.values():
            for kw in keywords:
                jieba.add_word(kw)
        for keywords in ATMOSPHERE_MAPPING.values():
            for kw in keywords:
                jieba.add_word(kw)

    def parse(self, query_text):
        """解析用户自然语言查询

        Args:
            query_text: 用户输入，如 "想吃辣的安静的餐厅，人均100左右"

        Returns:
            dict: {
                "flavors": ["辣"],
                "atmospheres": ["安静"],
                "price_range": (80, 120),
                "categories": [],
                "dishes": [],
                "keywords": ["辣", "安静"],
            }
        """
        result = {
            "flavors": [],
            "atmospheres": [],
            "price_range": None,
            "categories": [],
            "dishes": [],
            "keywords": [],
        }

        result["flavors"] = self._extract_flavors(query_text)
        result["atmospheres"] = self._extract_atmospheres(query_text)
        result["price_range"] = self._extract_price(query_text)
        result["categories"] = self._extract_categories(query_text)
        result["keywords"] = list(jieba.cut(query_text))

        return result

    def _extract_flavors(self, text):
        flavors = []
        for flavor, keywords in FLAVOR_MAPPING.items():
            if any(kw in text for kw in keywords):
                flavors.append(flavor)
        return flavors

    def _extract_atmospheres(self, text):
        atmospheres = []
        for atm, keywords in ATMOSPHERE_MAPPING.items():
            if any(kw in text for kw in keywords):
                atmospheres.append(atm)
        return atmospheres

    def _extract_price(self, text):
        for pattern, extractor in PRICE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return extractor(match)
        return None

    def _extract_categories(self, text):
        categories = []
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                categories.append(cat)
        return categories
