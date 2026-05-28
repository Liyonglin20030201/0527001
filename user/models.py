"""用户数据模型"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime


@dataclass
class User:
    """用户"""
    id: int
    nickname: str
    session_token: str
    created_at: str = ""


@dataclass
class UserProfile:
    """用户偏好画像"""
    user_id: int
    flavor_preferences: Dict[str, float] = field(default_factory=dict)
    atmosphere_preferences: Dict[str, float] = field(default_factory=dict)
    category_preferences: Dict[str, float] = field(default_factory=dict)
    price_range_low: float = 0
    price_range_high: float = 200
    updated_at: str = ""

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "flavor_preferences": self.flavor_preferences,
            "atmosphere_preferences": self.atmosphere_preferences,
            "category_preferences": self.category_preferences,
            "price_range": [self.price_range_low, self.price_range_high],
            "updated_at": self.updated_at,
        }


@dataclass
class BehaviorEvent:
    """行为事件"""
    id: Optional[int] = None
    user_id: int = 0
    event_type: str = ""
    restaurant_id: str = ""
    query_text: str = ""
    rating: Optional[int] = None
    metadata: str = ""
    created_at: str = ""
