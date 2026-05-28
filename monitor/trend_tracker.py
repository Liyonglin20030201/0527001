"""热门趋势检测"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from config import Config


class TrendTracker:
    """检测热门趋势餐厅

    通过定期快照餐厅的评论数和评分，对比历史数据检测:
    - 评论数激增 (>50% 增长视为趋势)
    - 评分显著变化 (>0.5分变动)
    """

    REVIEW_SPIKE_THRESHOLD = 1.5
    SCORE_CHANGE_THRESHOLD = 0.5

    def __init__(self, db_path=None):
        self.db_path = db_path or Config.SQLITE_PATH
        self._init_db()

    def _init_db(self):
        """确保快照表存在"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id TEXT NOT NULL,
                restaurant_name TEXT,
                platform TEXT NOT NULL,
                review_count INTEGER NOT NULL,
                overall_score REAL,
                snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_restaurant
            ON data_snapshots(restaurant_id, snapshot_at)
        """)
        conn.commit()
        conn.close()

    def take_snapshot(self):
        """从聚合数据中获取当前状态并保存快照"""
        aggregated_path = os.path.join("data", "aggregated_restaurants.jsonl")
        if not os.path.exists(aggregated_path):
            return

        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()

        with open(aggregated_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                name = data.get("name", "")
                restaurant_id = name
                platforms = data.get("source_platforms", ["unknown"])

                for platform in platforms:
                    conn.execute("""
                        INSERT INTO data_snapshots
                        (restaurant_id, restaurant_name, platform, review_count, overall_score, snapshot_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        restaurant_id,
                        name,
                        platform,
                        data.get("review_count", 0),
                        data.get("overall_score", 0),
                        now,
                    ))

        conn.commit()
        conn.close()

    def get_trending(self, days=7):
        """获取最近N天的趋势餐厅

        Returns:
            list of dict: [{name, review_growth, score_change, trend_type}, ...]
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        rows = conn.execute("""
            SELECT restaurant_id, restaurant_name,
                   MIN(review_count) as min_reviews,
                   MAX(review_count) as max_reviews,
                   MIN(overall_score) as min_score,
                   MAX(overall_score) as max_score,
                   COUNT(*) as snapshot_count
            FROM data_snapshots
            WHERE snapshot_at >= ?
            GROUP BY restaurant_id
            HAVING snapshot_count >= 2
        """, (cutoff,)).fetchall()

        conn.close()

        trending = []
        for row in rows:
            trend = {
                "name": row["restaurant_name"] or row["restaurant_id"],
                "review_growth": 0,
                "score_change": 0,
                "trend_type": [],
            }

            if row["min_reviews"] > 0:
                growth = row["max_reviews"] / row["min_reviews"]
                if growth >= self.REVIEW_SPIKE_THRESHOLD:
                    trend["review_growth"] = round((growth - 1) * 100, 1)
                    trend["trend_type"].append("review_spike")

            score_change = row["max_score"] - row["min_score"]
            if abs(score_change) >= self.SCORE_CHANGE_THRESHOLD:
                trend["score_change"] = round(score_change, 2)
                trend["trend_type"].append("score_change")

            if trend["trend_type"]:
                trending.append(trend)

        trending.sort(key=lambda x: x["review_growth"] + abs(x["score_change"]), reverse=True)
        return trending
