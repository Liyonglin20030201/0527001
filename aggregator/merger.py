"""多源数据合并"""

from aggregator.models import UnifiedRestaurant, SourceRecord


class DataMerger:
    """将去重后的多平台数据合并为统一记录

    合并策略:
    - 名称: 取最长的（通常更完整）
    - 价格: 取均值
    - 评分: 按评论数加权平均
    - 标签/推荐菜: 取并集
    - 分类: 取并集
    """

    def merge(self, groups):
        """对每组同一餐厅的多平台数据进行合并

        Args:
            groups: list of list, 每组是同一餐厅在不同平台的记录

        Returns:
            list of UnifiedRestaurant
        """
        results = []
        for group in groups:
            unified = self._merge_group(group)
            results.append(unified)
        return results

    def _merge_group(self, records):
        """合并一组记录"""
        names = [r.get("name", "") for r in records]
        best_name = max(names, key=len) if names else ""

        addresses = [r.get("address", "") for r in records if r.get("address")]
        best_address = max(addresses, key=len) if addresses else ""

        phones = [r.get("phone", "") for r in records if r.get("phone")]
        best_phone = phones[0] if phones else ""

        all_categories = set()
        for r in records:
            cats = r.get("category", [])
            if isinstance(cats, list):
                all_categories.update(cats)

        prices = []
        for r in records:
            try:
                p = float(r.get("avg_price", 0))
                if p > 0:
                    prices.append(p)
            except (ValueError, TypeError):
                pass
        avg_price = round(sum(prices) / len(prices), 1) if prices else 0

        scores = []
        weights = []
        for r in records:
            try:
                s = float(r.get("overall_score", 0))
                w = int(r.get("review_count", 1)) or 1
                if s > 0:
                    scores.append(s)
                    weights.append(w)
            except (ValueError, TypeError):
                pass

        if scores:
            total_weight = sum(weights)
            overall_score = round(
                sum(s * w for s, w in zip(scores, weights)) / total_weight, 2
            )
        else:
            overall_score = 0

        all_tags = set()
        for r in records:
            tags = r.get("tags", [])
            if isinstance(tags, list):
                all_tags.update(tags)

        all_dishes = set()
        for r in records:
            dishes = r.get("recommended_dishes", [])
            if isinstance(dishes, list):
                all_dishes.update(dishes)

        platforms = list(set(r.get("source_platform", "unknown") for r in records))

        total_reviews = sum(int(r.get("review_count", 0)) for r in records)

        source_records = []
        for r in records:
            try:
                price_val = float(r.get("avg_price", 0))
            except (ValueError, TypeError):
                price_val = 0
            try:
                score_val = float(r.get("overall_score", 0))
            except (ValueError, TypeError):
                score_val = 0

            source_records.append(SourceRecord(
                platform=r.get("source_platform", "unknown"),
                name=r.get("name", ""),
                address=r.get("address", ""),
                phone=r.get("phone", ""),
                category=r.get("category", []),
                avg_price=price_val,
                overall_score=score_val,
                url=r.get("url", ""),
                tags=r.get("tags", []),
                recommended_dishes=r.get("recommended_dishes", []),
                review_count=int(r.get("review_count", 0)),
            ))

        return UnifiedRestaurant(
            name=best_name,
            address=best_address,
            phone=best_phone,
            category=list(all_categories),
            avg_price=avg_price,
            overall_score=overall_score,
            tags=list(all_tags),
            recommended_dishes=list(all_dishes),
            source_platforms=platforms,
            source_records=source_records,
            review_count=total_reviews,
        )
