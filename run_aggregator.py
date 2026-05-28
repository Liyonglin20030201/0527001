"""运行多平台数据聚合流程

使用方式:
    python run_aggregator.py

功能:
    1. 从各平台的模拟数据加载餐厅信息
    2. 跨平台去重（名称+地址模糊匹配）
    3. 合并同一餐厅的多平台数据
    4. 计算可信度评分
    5. 输出统一格式的聚合结果
"""

import json
import os

from aggregator.deduplicator import RestaurantDeduplicator
from aggregator.merger import DataMerger
from aggregator.confidence import ConfidenceScorer


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


def main():
    print("=" * 60)
    print("多平台数据聚合流程")
    print("=" * 60)

    all_records = []
    platforms = ["meituan", "eleme"]

    for platform in platforms:
        records = load_platform_data(platform)
        print(f"\n[{platform}] 加载了 {len(records)} 条餐厅数据")
        all_records.extend(records)

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

    print("\n>> 步骤3: 计算可信度...")
    scorer = ConfidenceScorer()
    for record in unified:
        record.confidence_score = scorer.score(record)

    print("\n" + "=" * 60)
    print("聚合结果:")
    print("=" * 60)

    for r in unified:
        platforms_str = ", ".join(r.source_platforms)
        print(f"\n  [{r.confidence_score:.2f}] {r.name}")
        print(f"        地址: {r.address}")
        print(f"        价格: ¥{r.avg_price} | 评分: {r.overall_score}")
        print(f"        分类: {', '.join(r.category)}")
        print(f"        标签: {', '.join(r.tags[:5])}")
        print(f"        来源: {platforms_str}")

    output_path = os.path.join("data", "aggregated_restaurants.jsonl")
    with open(output_path, "w", encoding="utf-8") as f:
        for r in unified:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

    print(f"\n\n已保存聚合结果到: {output_path}")


if __name__ == "__main__":
    main()
