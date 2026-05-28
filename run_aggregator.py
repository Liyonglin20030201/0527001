"""运行多平台数据聚合流程

使用方式:
    python run_aggregator.py

功能:
    1. 从各平台的模拟数据加载餐厅信息
    2. 跨平台去重（名称+地址模糊匹配）
    3. 合并同一餐厅的多平台数据
    4. 从评论中提取口味/氛围标签
    5. 计算可信度评分
    6. 输出统一格式的聚合结果（可直接导入ES）
"""

import json
import os
from collections import defaultdict

from aggregator.deduplicator import RestaurantDeduplicator
from aggregator.merger import DataMerger
from aggregator.confidence import ConfidenceScorer


FLAVOR_KEYWORDS = {
    "辣": ["辣", "麻辣", "微辣", "变态辣", "香辣"],
    "清淡": ["清淡", "少油", "少盐", "养生"],
    "甜": ["甜", "甜品", "甜点", "蜜"],
    "鲜": ["鲜", "海鲜", "新鲜"],
    "酸": ["酸", "酸辣", "酸甜"],
}

ATMOSPHERE_KEYWORDS = {
    "安静": ["安静", "静", "清静", "幽静"],
    "浪漫": ["浪漫", "情调", "约会", "情侣"],
    "家庭": ["家庭", "亲子", "带孩子", "老人"],
    "商务": ["商务", "宴请", "接待", "包间"],
    "热闹": ["热闹", "氛围好", "聚餐", "聚会"],
    "文艺": ["文艺", "小资", "ins风", "网红"],
}


def load_platform_data(platform_name):
    """加载某平台的模拟餐厅数据"""
    file_path = os.path.join("data", "mock", f"{platform_name}_restaurants.jsonl")
    records = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    data["source_platform"] = platform_name
                    records.append(data)
    return records


def load_platform_reviews(platform_name):
    """加载某平台的评论数据"""
    file_path = os.path.join("data", "mock", f"{platform_name}_reviews.jsonl")
    reviews = defaultdict(list)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    reviews[data.get("restaurant_name", "")].append(data)
    return reviews


def extract_flavor_tags(reviews):
    """从评论中提取口味标签"""
    tag_counts = defaultdict(int)
    for review in reviews:
        content = review.get("content", "")
        for tag, keywords in FLAVOR_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                tag_counts[tag] += 1
    threshold = max(len(reviews) * 0.1, 1)
    return [tag for tag, count in tag_counts.items() if count >= threshold]


def extract_atmosphere_tags(reviews):
    """从评论中提取氛围标签"""
    tag_counts = defaultdict(int)
    for review in reviews:
        content = review.get("content", "")
        for tag, keywords in ATMOSPHERE_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                tag_counts[tag] += 1
    threshold = max(len(reviews) * 0.1, 1)
    return [tag for tag, count in tag_counts.items() if count >= threshold]


def main():
    print("=" * 60)
    print("多平台数据聚合流程")
    print("=" * 60)

    all_records = []
    all_reviews = defaultdict(list)
    platforms = ["meituan", "eleme"]

    for platform in platforms:
        records = load_platform_data(platform)
        reviews = load_platform_reviews(platform)
        print(f"\n[{platform}] 加载了 {len(records)} 条餐厅数据, "
              f"{sum(len(v) for v in reviews.values())} 条评论")
        all_records.extend(records)
        for name, rev_list in reviews.items():
            all_reviews[name].extend(rev_list)

    print(f"\n总计: {len(all_records)} 条原始记录")
    print("-" * 60)

    print("\n>> 步骤1: 跨平台去重...")
    deduplicator = RestaurantDeduplicator()
    groups = deduplicator.deduplicate(all_records)
    multi_source = sum(1 for g in groups if len(g) > 1)
    print(f"   去重后: {len(groups)} 个独立餐厅 (其中 {multi_source} 个跨平台匹配)")

    print("\n>> 步骤2: 合并多源数据...")
    merger = DataMerger()
    unified = merger.merge(groups)
    print(f"   生成 {len(unified)} 条统一记录")

    print("\n>> 步骤3: 提取标签 + 计算可信度...")
    scorer = ConfidenceScorer()
    for record in unified:
        name = record.name
        reviews = all_reviews.get(name, [])
        if not reviews:
            for alt_name in all_reviews:
                if name in alt_name or alt_name in name:
                    reviews = all_reviews[alt_name]
                    break

        record.review_count = max(record.review_count, len(reviews))
        record.confidence_score = scorer.score(record)

    print("\n" + "=" * 60)
    print("聚合结果:")
    print("=" * 60)

    for r in unified:
        platforms_str = ", ".join(r.source_platforms)
        print(f"\n  [{r.confidence_score:.2f}] {r.name}")
        print(f"        地址: {r.address}")
        print(f"        价格: {r.avg_price}元 | 评分: {r.overall_score}")
        print(f"        分类: {', '.join(r.category)}")
        print(f"        标签: {', '.join(r.tags[:5])}")
        print(f"        来源: {platforms_str}")

    output_path = os.path.join("data", "aggregated_restaurants.jsonl")
    with open(output_path, "w", encoding="utf-8") as f:
        for r in unified:
            doc = r.to_dict()
            name = r.name
            reviews = all_reviews.get(name, [])
            if not reviews:
                for alt_name in all_reviews:
                    if name in alt_name or alt_name in name:
                        reviews = all_reviews[alt_name]
                        break

            doc["flavor_tags"] = extract_flavor_tags(reviews)
            doc["atmosphere_tags"] = extract_atmosphere_tags(reviews)
            doc["review_count"] = max(doc.get("review_count", 0), len(reviews))
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"\n\n已保存聚合结果到: {output_path}")


if __name__ == "__main__":
    main()
