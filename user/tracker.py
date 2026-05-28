"""用户行为追踪"""

import json
from datetime import datetime
from user.db import UserDB


class BehaviorTracker:
    """记录用户行为事件

    事件类型:
    - search: 用户搜索（记录查询文本和返回结果）
    - click: 点击查看某家餐厅
    - favorite: 收藏/取消收藏
    - rate: 用户评分
    """

    def __init__(self, db=None):
        self.db = db or UserDB()

    def track_search(self, user_id, query_text, result_ids=None):
        """记录搜索行为"""
        metadata = json.dumps({"result_ids": result_ids or []}, ensure_ascii=False)
        self._insert_event(user_id, "search", query_text=query_text, metadata=metadata)

    def track_click(self, user_id, restaurant_id):
        """记录点击行为"""
        self._insert_event(user_id, "click", restaurant_id=restaurant_id)

    def track_favorite(self, user_id, restaurant_id):
        """记录收藏行为"""
        self._insert_event(user_id, "favorite", restaurant_id=restaurant_id)

        conn = self.db.get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO favorites (user_id, restaurant_id) VALUES (?, ?)",
                (user_id, restaurant_id),
            )
            conn.commit()
        finally:
            conn.close()

    def remove_favorite(self, user_id, restaurant_id):
        """取消收藏"""
        conn = self.db.get_connection()
        try:
            conn.execute(
                "DELETE FROM favorites WHERE user_id = ? AND restaurant_id = ?",
                (user_id, restaurant_id),
            )
            conn.commit()
        finally:
            conn.close()

    def track_rating(self, user_id, restaurant_id, rating):
        """记录评分行为"""
        self._insert_event(user_id, "rate", restaurant_id=restaurant_id, rating=rating)

    def get_user_events(self, user_id, event_type=None, limit=100):
        """获取用户的行为历史"""
        conn = self.db.get_connection()
        try:
            if event_type:
                rows = conn.execute(
                    "SELECT * FROM behavior_events WHERE user_id = ? AND event_type = ? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (user_id, event_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM behavior_events WHERE user_id = ? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_favorites(self, user_id):
        """获取用户收藏列表"""
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                "SELECT restaurant_id, created_at FROM favorites "
                "WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_event_count(self, user_id):
        """获取用户行为总数"""
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM behavior_events WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return row["count"]
        finally:
            conn.close()

    def _insert_event(self, user_id, event_type, restaurant_id=None,
                      query_text=None, rating=None, metadata=None):
        """插入行为事件"""
        conn = self.db.get_connection()
        try:
            conn.execute(
                "INSERT INTO behavior_events "
                "(user_id, event_type, restaurant_id, query_text, rating, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, event_type, restaurant_id, query_text, rating, metadata),
            )
            conn.commit()
        finally:
            conn.close()
