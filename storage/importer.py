"""将爬虫+情感分析结果聚合并导入Elasticsearch"""

import json
import os
from collections import defaultdict
from storage.es_storage import ElasticStorage


def aggregate_restaurant_data(restaurants_path, reviews_analyzed_path):
    """将餐厅数据和分析后的评论聚合为ES文档

    聚合逻辑：
    1. 以餐厅为单位汇总所有评论的情感分析结果
    2. 计算各维度情感均分
    3. 统计各菜品的好评率
    4. 提取口味标签和氛围标签
    """
    restaurants = {}
    with open(restaurants_path, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line.strip())
            restaurants[r["name"]] = r

    review_data = defaultdict(list)
    with open(reviews_analyzed_path, "r", encoding="utf-8") as f:
        for line in f:
            review = json.loads(line.strip())
            review_data[review["restaurant_name"]].append(review)

    docs = []
    for name, restaurant in restaurants.items():
        reviews = review_data.get(name, [])
        doc = _build_document(restaurant, reviews)
        docs.append(doc)

    return docs


def _build_document(restaurant, reviews):
    """构建单个餐厅的ES文档"""
    doc = {
        "name": restaurant.get("name", ""),
        "address": restaurant.get("address", ""),
        "phone": restaurant.get("phone", ""),
        "category": restaurant.get("category", []),
        "url": restaurant.get("url", ""),
        "tags": restaurant.get("tags", []),
        "recommended_dishes": restaurant.get("recommended_dishes", []),
        "review_count": len(reviews),
    }

    avg_price = restaurant.get("avg_price", "")
    try:
        doc["avg_price"] = float(avg_price.replace("￥", "").replace("¥", "").strip())
    except (ValueError, AttributeError):
        doc["avg_price"] = 0.0

    try:
        doc["overall_score"] = float(restaurant.get("overall_score", "0"))
    except (ValueError, TypeError):
        doc["overall_score"] = 0.0

    doc["sentiment_summary"] = _compute_sentiment_summary(reviews)
    doc["dish_sentiments"] = _compute_dish_sentiments(reviews)
    doc["flavor_tags"] = _extract_flavor_tags(reviews)
    doc["atmosphere_tags"] = _extract_atmosphere_tags(reviews)

    return doc


def _compute_sentiment_summary(reviews):
    """计算各维度情感均分"""
    aspect_scores = defaultdict(list)
    overall_scores = []

    for review in reviews:
        sentiment = review.get("sentiment", {})
        if sentiment.get("label") == "positive":
            overall_scores.append(sentiment.get("score", 0.5))
        elif sentiment.get("label") == "negative":
            overall_scores.append(-sentiment.get("score", 0.5))
        else:
            overall_scores.append(0.0)

        aspects = review.get("aspects", {})
        for aspect, score in aspects.items():
            aspect_scores[aspect].append(score)

    summary = {
        "overall": round(sum(overall_scores) / max(len(overall_scores), 1), 3),
    }
    for aspect in ["taste", "environment", "service", "price"]:
        scores = aspect_scores.get(aspect, [])
        summary[aspect] = round(sum(scores) / max(len(scores), 1), 3) if scores else 0.0

    return summary


def _compute_dish_sentiments(reviews):
    """计算各菜品的好评率"""
    dish_stats = defaultdict(lambda: {"positive": 0, "total": 0, "samples": []})

    for review in reviews:
        dish_sentiments = review.get("dish_sentiments", {})
        for dish_name, result in dish_sentiments.items():
            if not result.get("mentioned"):
                continue
            dish_stats[dish_name]["total"] += 1
            if result.get("label") == "positive":
                dish_stats[dish_name]["positive"] += 1
            if len(dish_stats[dish_name]["samples"]) < 3:
                dish_stats[dish_name]["samples"].append(
                    review.get("content", "")[:100]
                )

    results = []
    for dish_name, stats in dish_stats.items():
        results.append({
            "dish_name": dish_name,
            "positive_rate": round(stats["positive"] / max(stats["total"], 1), 3),
            "mention_count": stats["total"],
            "sample_reviews": " | ".join(stats["samples"]),
        })

    return sorted(results, key=lambda x: x["mention_count"], reverse=True)[:20]


FLAVOR_KEYWORDS = {
    "辣": ["辣", "麻辣", "微辣", "变态辣", "香辣"],
    "清淡": ["清淡", "少油", "少盐", "养生"],
    "甜": ["甜", "甜品", "甜点", "蜜"],
    "鲜": ["鲜", "海鲜", "新鲜"],
    "酸": ["酸", "酸辣", "酸甜"],
    "油腻": ["油腻", "重油"],
}

ATMOSPHERE_KEYWORDS = {
    "安静": ["安静", "静", "清静", "幽静"],
    "浪漫": ["浪漫", "情调", "约会", "情侣"],
    "家庭": ["家庭", "亲子", "带孩子", "老人"],
    "商务": ["商务", "宴请", "接待", "包间"],
    "热闹": ["热闹", "氛围好", "聚餐", "聚会"],
    "文艺": ["文艺", "小资", "ins风", "网红"],
}


def _extract_flavor_tags(reviews):
    """从评论中提取口味标签"""
    tag_counts = defaultdict(int)
    for review in reviews:
        content = review.get("content", "")
        for tag, keywords in FLAVOR_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                tag_counts[tag] += 1

    threshold = max(len(reviews) * 0.1, 2)
    return [tag for tag, count in tag_counts.items() if count >= threshold]


def _extract_atmosphere_tags(reviews):
    """从评论中提取氛围标签"""
    tag_counts = defaultdict(int)
    for review in reviews:
        content = review.get("content", "")
        for tag, keywords in ATMOSPHERE_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                tag_counts[tag] += 1

    threshold = max(len(reviews) * 0.1, 2)
    return [tag for tag, count in tag_counts.items() if count >= threshold]


def import_to_es(docs):
    """将文档导入Elasticsearch"""
    storage = ElasticStorage()
    storage.create_index()
    storage.bulk_index(docs)
    return len(docs)


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    docs = aggregate_restaurant_data(
        os.path.join(data_dir, "restaurants.jsonl"),
        os.path.join(data_dir, "reviews_analyzed.jsonl"),
    )
    count = import_to_es(docs)
    print(f"成功导入 {count} 家餐厅数据到 Elasticsearch")
