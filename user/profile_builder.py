"""用户偏好画像构建"""

import json
import math
from datetime import datetime, timedelta
from collections import defaultdict

from user.db import UserDB


class ProfileBuilder:
    """从用户行为历史构建偏好向量

    算法:
    1. 收集用户所有点击/收藏/评分的餐厅
    2. 对每个行为赋予权重 (收藏>评分>点击)
    3. 应用时间衰减 (近期行为权重更大)
    4. 统计各维度标签频率，生成偏好向量
    """

    DECAY_FACTOR = 0.95
    EVENT_WEIGHTS = {
        "favorite": 3.0,
        "rate": 2.0,
        "click": 1.0,
        "search": 0.5,
    }
    MIN_EVENTS_FOR_PROFILE = 5

    def __init__(self, db=None):
        self.db = db or UserDB()

    def build_profile(self, user_id, restaurant_lookup=None):
        """构建用户偏好画像

        Args:
            user_id: 用户ID
            restaurant_lookup: 可选的餐厅数据查找函数 (restaurant_id -> dict)

        Returns:
            dict: {
                "flavor_preferences": {"辣": 0.8, "鲜": 0.5, ...},
                "atmosphere_preferences": {"安静": 0.7, ...},
                "category_preferences": {"川菜": 0.9, ...},
                "price_range": [80, 150],
                "ready": True/False (行为是否足够)
            }
        """
        conn = self.db.get_connection()
        try:
            events = conn.execute(
                "SELECT * FROM behavior_events WHERE user_id = ? "
                "AND restaurant_id IS NOT NULL AND restaurant_id != '' "
                "ORDER BY created_at DESC LIMIT 200",
                (user_id,),
            ).fetchall()
        finally:
            conn.close()

        if len(events) < self.MIN_EVENTS_FOR_PROFILE:
            return {
                "flavor_preferences": {},
                "atmosphere_preferences": {},
                "category_preferences": {},
                "price_range": [0, 200],
                "ready": False,
                "event_count": len(events),
            }

        flavor_scores = defaultdict(float)
        atmosphere_scores = defaultdict(float)
        category_scores = defaultdict(float)
        prices = []

        now = datetime.now()

        for event in events:
            event_dict = dict(event)
            restaurant_id = event_dict["restaurant_id"]
            event_type = event_dict["event_type"]
            created_at = event_dict["created_at"]

            base_weight = self.EVENT_WEIGHTS.get(event_type, 1.0)

            if event_type == "rate" and event_dict.get("rating"):
                rating = event_dict["rating"]
                base_weight *= (rating / 5.0)

            try:
                event_time = datetime.fromisoformat(created_at)
                days_ago = (now - event_time).days
            except (ValueError, TypeError):
                days_ago = 30
            time_weight = self.DECAY_FACTOR ** days_ago

            weight = base_weight * time_weight

            restaurant = None
            if restaurant_lookup:
                restaurant = restaurant_lookup(restaurant_id)

            if restaurant:
                for tag in restaurant.get("flavor_tags", []):
                    flavor_scores[tag] += weight
                for tag in restaurant.get("atmosphere_tags", []):
                    atmosphere_scores[tag] += weight
                for cat in restaurant.get("category", []):
                    category_scores[cat] += weight
                price = restaurant.get("avg_price", 0)
                if price and price > 0:
                    prices.append(price)
            else:
                metadata = event_dict.get("metadata", "")
                if metadata:
                    try:
                        meta = json.loads(metadata)
                        for tag in meta.get("flavor_tags", []):
                            flavor_scores[tag] += weight
                        for tag in meta.get("atmosphere_tags", []):
                            atmosphere_scores[tag] += weight
                        for cat in meta.get("category", []):
                            category_scores[cat] += weight
                    except (json.JSONDecodeError, TypeError):
                        pass

        profile = {
            "flavor_preferences": self._normalize_scores(flavor_scores),
            "atmosphere_preferences": self._normalize_scores(atmosphere_scores),
            "category_preferences": self._normalize_scores(category_scores),
            "price_range": self._compute_price_range(prices),
            "ready": True,
            "event_count": len(events),
        }

        self._save_profile(user_id, profile)
        return profile

    def get_cached_profile(self, user_id):
        """获取缓存的画像（不重新计算）"""
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()

            if not row:
                return None

            return {
                "flavor_preferences": json.loads(row["flavor_preferences"]),
                "atmosphere_preferences": json.loads(row["atmosphere_preferences"]),
                "category_preferences": json.loads(row["category_preferences"]),
                "price_range": [row["price_range_low"], row["price_range_high"]],
                "ready": True,
                "updated_at": row["updated_at"],
            }
        finally:
            conn.close()

    def _normalize_scores(self, scores):
        """将分数归一化到 0-1 范围"""
        if not scores:
            return {}
        max_score = max(scores.values())
        if max_score == 0:
            return {}
        return {k: round(v / max_score, 3) for k, v in scores.items()}

    def _compute_price_range(self, prices):
        """根据历史价格计算偏好价格区间"""
        if not prices:
            return [0, 200]
        prices.sort()
        low = prices[int(len(prices) * 0.2)]
        high = prices[int(len(prices) * 0.8)]
        margin = (high - low) * 0.2
        return [max(0, round(low - margin)), round(high + margin)]

    def _save_profile(self, user_id, profile):
        """保存画像到数据库"""
        conn = self.db.get_connection()
        try:
            price_range = profile["price_range"]
            conn.execute("""
                INSERT INTO user_profiles (user_id, flavor_preferences, atmosphere_preferences,
                    category_preferences, price_range_low, price_range_high, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    flavor_preferences = excluded.flavor_preferences,
                    atmosphere_preferences = excluded.atmosphere_preferences,
                    category_preferences = excluded.category_preferences,
                    price_range_low = excluded.price_range_low,
                    price_range_high = excluded.price_range_high,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                user_id,
                json.dumps(profile["flavor_preferences"], ensure_ascii=False),
                json.dumps(profile["atmosphere_preferences"], ensure_ascii=False),
                json.dumps(profile["category_preferences"], ensure_ascii=False),
                price_range[0],
                price_range[1],
            ))
            conn.commit()
        finally:
            conn.close()
