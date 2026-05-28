"""跨平台数据可信度评分"""

import math


class ConfidenceScorer:
    """基于多维度因子计算数据可信度

    评分因子:
    - platform_count: 出现在几个平台 (越多越可信)
    - review_count: 总评论数 (越多越可信)
    - score_consistency: 各平台评分是否一致 (越一致越可信)
    - data_completeness: 关键字段是否齐全

    最终得分范围: 0.0 - 1.0
    """

    PLATFORM_WEIGHT = 0.35
    REVIEW_WEIGHT = 0.25
    CONSISTENCY_WEIGHT = 0.25
    COMPLETENESS_WEIGHT = 0.15

    def score(self, unified_record):
        """计算可信度分数

        Args:
            unified_record: UnifiedRestaurant 实例或字典

        Returns:
            float: 0.0 - 1.0
        """
        if hasattr(unified_record, "source_platforms"):
            platforms = unified_record.source_platforms
            source_records = unified_record.source_records
            review_count = unified_record.review_count
            record_dict = unified_record.to_dict()
        else:
            platforms = unified_record.get("source_platforms", [])
            source_records = unified_record.get("source_records", [])
            review_count = unified_record.get("review_count", 0)
            record_dict = unified_record

        platform_score = self._score_platforms(platforms)
        review_score = self._score_reviews(review_count)
        consistency_score = self._score_consistency(source_records)
        completeness_score = self._score_completeness(record_dict)

        final = (
            self.PLATFORM_WEIGHT * platform_score
            + self.REVIEW_WEIGHT * review_score
            + self.CONSISTENCY_WEIGHT * consistency_score
            + self.COMPLETENESS_WEIGHT * completeness_score
        )

        return round(min(final, 1.0), 3)

    def _score_platforms(self, platforms):
        """平台覆盖度评分: 1个=0.4, 2个=0.7, 3个+=1.0"""
        count = len(platforms)
        if count >= 3:
            return 1.0
        elif count == 2:
            return 0.7
        elif count == 1:
            return 0.4
        return 0.0

    def _score_reviews(self, review_count):
        """评论数评分: 使用对数缩放, 100条=1.0"""
        if review_count <= 0:
            return 0.1
        return min(math.log10(review_count + 1) / 2.0, 1.0)

    def _score_consistency(self, source_records):
        """评分一致性: 各平台评分标准差越小越好"""
        scores = []
        for r in source_records:
            s = r.overall_score if hasattr(r, "overall_score") else r.get("overall_score", 0)
            if s > 0:
                scores.append(s)

        if len(scores) <= 1:
            return 0.5

        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std_dev = math.sqrt(variance)

        return max(0.0, 1.0 - std_dev / 2.0)

    def _score_completeness(self, record_dict):
        """字段完整度评分"""
        required_fields = ["name", "address", "category", "avg_price", "overall_score", "tags"]
        filled = 0
        for field in required_fields:
            value = record_dict.get(field)
            if value and (not isinstance(value, (list, str)) or len(value) > 0):
                filled += 1
        return filled / len(required_fields)
