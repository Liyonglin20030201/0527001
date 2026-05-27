"""运行情感分析处理的入口脚本"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sentiment.process import process_reviews


def main():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    reviews_path = os.path.join(data_dir, "reviews.jsonl")
    output_path = os.path.join(data_dir, "reviews_analyzed.jsonl")

    if not os.path.exists(reviews_path):
        print(f"错误：找不到评论文件 {reviews_path}")
        print("请先运行爬虫：python run_crawler.py")
        sys.exit(1)

    print(f"正在分析评论... (输入: {reviews_path})")
    process_reviews(reviews_path, output_path)
    print(f"分析完成，结果保存到: {output_path}")


if __name__ == "__main__":
    main()
