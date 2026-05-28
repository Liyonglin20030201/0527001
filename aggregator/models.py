"""统一数据模型"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class SourceRecord:
    """单个平台的餐厅数据"""
    platform: str
    name: str
    address: str
    phone: str
    category: List[str]
    avg_price: float
    overall_score: float
    url: str
    tags: List[str]
    recommended_dishes: List[str]
    review_count: int = 0


@dataclass
class UnifiedRestaurant:
    """合并后的统一餐厅数据"""
    name: str
    address: str
    phone: str
    category: List[str]
    avg_price: float
    overall_score: float
    tags: List[str]
    recommended_dishes: List[str]
    source_platforms: List[str] = field(default_factory=list)
    source_records: List[SourceRecord] = field(default_factory=list)
    confidence_score: float = 0.0
    review_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "category": self.category,
            "avg_price": self.avg_price,
            "overall_score": self.overall_score,
            "tags": self.tags,
            "recommended_dishes": self.recommended_dishes,
            "source_platforms": self.source_platforms,
            "confidence_score": self.confidence_score,
            "review_count": self.review_count,
        }
