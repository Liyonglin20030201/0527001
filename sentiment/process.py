import json
import os
from sentiment.analyzer import SentimentAnalyzer


def process_reviews(reviews_path, output_path):
    """批量处理评论文件，输出带情感标签的结果

    Args:
        reviews_path: reviews.jsonl 文件路径
        output_path: 输出文件路径
    """
    analyzer = SentimentAnalyzer()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(reviews_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:

        batch_texts = []
        batch_items = []

        for line in fin:
            item = json.loads(line.strip())
            if not item.get("content"):
                continue

            batch_texts.append(item["content"])
            batch_items.append(item)

            if len(batch_texts) >= 16:
                _flush_batch(analyzer, batch_texts, batch_items, fout)
                batch_texts = []
                batch_items = []

        if batch_texts:
            _flush_batch(analyzer, batch_texts, batch_items, fout)


def _flush_batch(analyzer, texts, items, fout):
    results = analyzer.batch_analyze(texts)
    for item, sentiment in zip(items, results):
        item["sentiment"] = sentiment

        if item.get("dishes_mentioned"):
            dish_sentiments = {}
            for dish in item["dishes_mentioned"]:
                dish_result = analyzer.analyze_dish(item["content"], dish)
                dish_sentiments[dish] = dish_result
            item["dish_sentiments"] = dish_sentiments

        aspect_result = analyzer.analyze(item["content"])
        item["aspects"] = aspect_result["aspects"]

        fout.write(json.dumps(item, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    process_reviews(
        os.path.join(data_dir, "reviews.jsonl"),
        os.path.join(data_dir, "reviews_analyzed.jsonl"),
    )
