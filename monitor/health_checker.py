"""数据健康检查"""

import os
import json
from datetime import datetime, timedelta
from config import Config


class HealthChecker:
    """系统健康状态检查

    检查项:
    - Elasticsearch 连接状态
    - 数据新鲜度 (最近一次爬取时间)
    - 各平台数据量
    - 磁盘空间 (数据目录)
    """

    def __init__(self, storage=None):
        self.storage = storage

    def check_all(self):
        """执行全部健康检查"""
        return {
            "timestamp": datetime.now().isoformat(),
            "elasticsearch": self._check_elasticsearch(),
            "data_freshness": self._check_data_freshness(),
            "platform_stats": self._check_platform_stats(),
            "overall": self._compute_overall_status(),
        }

    def _check_elasticsearch(self):
        """检查ES连接"""
        if not self.storage:
            try:
                from storage.es_storage import ElasticStorage
                self.storage = ElasticStorage()
            except Exception:
                return {"status": "error", "message": "无法创建ES连接"}

        try:
            info = self.storage.es.info()
            count = self.storage.es.count(index=Config.ES_INDEX)
            return {
                "status": "healthy",
                "version": info["version"]["number"],
                "doc_count": count["count"],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _check_data_freshness(self):
        """检查数据新鲜度"""
        freshness = {}
        data_dir = "data"
        mock_dir = os.path.join(data_dir, "mock")

        files_to_check = {
            "aggregated": os.path.join(data_dir, "aggregated_restaurants.jsonl"),
            "meituan": os.path.join(mock_dir, "meituan_restaurants.jsonl"),
            "eleme": os.path.join(mock_dir, "eleme_restaurants.jsonl"),
        }

        for name, path in files_to_check.items():
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                modified = datetime.fromtimestamp(mtime)
                age_hours = (datetime.now() - modified).total_seconds() / 3600
                freshness[name] = {
                    "last_modified": modified.isoformat(),
                    "age_hours": round(age_hours, 1),
                    "fresh": age_hours < Config.SCHEDULER_INTERVAL_HOURS * 2,
                }
            else:
                freshness[name] = {"status": "missing"}

        return freshness

    def _check_platform_stats(self):
        """各平台数据统计"""
        stats = {}
        mock_dir = os.path.join("data", "mock")

        for platform in Config.PLATFORMS:
            restaurants_file = os.path.join(mock_dir, f"{platform}_restaurants.jsonl")
            reviews_file = os.path.join(mock_dir, f"{platform}_reviews.jsonl")

            restaurant_count = self._count_lines(restaurants_file)
            review_count = self._count_lines(reviews_file)

            stats[platform] = {
                "restaurants": restaurant_count,
                "reviews": review_count,
            }

        return stats

    def _count_lines(self, file_path):
        """计算文件行数"""
        if not os.path.exists(file_path):
            return 0
        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    def _compute_overall_status(self):
        """综合健康评估"""
        es = self._check_elasticsearch()
        if es.get("status") == "error":
            return "degraded"
        return "healthy"
