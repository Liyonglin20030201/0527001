"""一键启动脚本：初始化ES索引 + 导入示例数据 + 启动Flask服务"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from storage.importer import aggregate_restaurant_data, import_to_es, import_aggregated_to_es
from config import Config


def init_data():
    """初始化数据到ES

    优先使用原始数据（restaurants.jsonl + reviews_analyzed.jsonl），
    如果原始数据不存在，则尝试使用聚合数据（aggregated_restaurants.jsonl），
    如果聚合数据也不存在，则先运行聚合流程再导入。
    """
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    restaurants_path = os.path.join(data_dir, "restaurants.jsonl")
    reviews_path = os.path.join(data_dir, "reviews_analyzed.jsonl")
    aggregated_path = os.path.join(data_dir, "aggregated_restaurants.jsonl")

    if os.path.exists(restaurants_path):
        print("使用原始数据导入...")
        docs = aggregate_restaurant_data(restaurants_path, reviews_path)
        print(f"聚合完成，共 {len(docs)} 家餐厅")
        print("正在导入 Elasticsearch...")
        count = import_to_es(docs)
        print(f"成功导入 {count} 家餐厅")
        return True

    if not os.path.exists(aggregated_path):
        print("原始数据不存在，先运行多平台聚合...")
        try:
            from run_aggregator import main as run_aggregate
            run_aggregate()
        except Exception as e:
            print(f"聚合失败: {e}")
            return False

    if os.path.exists(aggregated_path):
        print("使用聚合数据导入...")
        count = import_aggregated_to_es(aggregated_path)
        if count > 0:
            print(f"成功导入 {count} 家餐厅")
            return True

    print("错误：没有可用的数据源")
    return False


def main():
    print("=" * 50)
    print("  餐厅智能推荐系统 - 启动")
    print("=" * 50)

    if "--init" in sys.argv or "--all" in sys.argv:
        print("\n[1/3] 初始化数据...")
        if not init_data():
            print("数据初始化失败，请检查Elasticsearch是否启动")
            if "--all" not in sys.argv:
                sys.exit(1)
    else:
        print("\n跳过数据初始化（使用 --init 参数初始化）")

    if "--scheduler" in sys.argv or "--all" in sys.argv:
        print("\n[2/3] 启动定时调度器...")
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not Config.FLASK_DEBUG:
            from monitor.scheduler import DataScheduler
            scheduler = DataScheduler()
            scheduler.start()
            print("  调度器已启动，定期执行数据更新任务")
        else:
            print("  (调度器将在reload子进程中启动)")
    else:
        print("\n跳过调度器（使用 --scheduler 参数启用）")

    if "--no-server" not in sys.argv:
        print(f"\n[3/3] 启动Flask服务 @ http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")
        print("按 Ctrl+C 停止服务\n")
        from app import app
        app.run(host=Config.FLASK_HOST, port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)


if __name__ == "__main__":
    main()
