"""SQLite 数据库管理"""

import os
import sqlite3
from config import Config


class UserDB:
    """SQLite 连接管理器

    使用 WAL 模式以支持并发读取，适合 Flask 多请求场景。
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or Config.SQLITE_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_schema()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self):
        """初始化表结构"""
        conn = self.get_connection()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS behavior_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                restaurant_id TEXT,
                query_text TEXT,
                rating INTEGER,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                flavor_preferences TEXT NOT NULL DEFAULT '{}',
                atmosphere_preferences TEXT NOT NULL DEFAULT '{}',
                category_preferences TEXT NOT NULL DEFAULT '{}',
                price_range_low REAL DEFAULT 0,
                price_range_high REAL DEFAULT 200,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, restaurant_id)
            );

            CREATE INDEX IF NOT EXISTS idx_behavior_user
            ON behavior_events(user_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_behavior_type
            ON behavior_events(event_type);
        """)
        conn.commit()
        conn.close()
