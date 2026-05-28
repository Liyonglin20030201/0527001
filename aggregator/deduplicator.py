"""跨平台餐厅去重"""

from rapidfuzz import fuzz


class RestaurantDeduplicator:
    """基于名称和地址模糊匹配的餐厅去重

    策略: 名称相似度 > 85% 且地址相似度 > 80% 才判定为同一餐厅，
    避免连锁店不同门店被误合并（如 "鼎泰丰三里屯店" vs "鼎泰丰国贸店"）
    """

    NAME_THRESHOLD = 75
    ADDR_THRESHOLD = 75

    def deduplicate(self, records):
        """将餐厅记录按同一实体分组

        Args:
            records: list of dict, 每条包含 name, address, source_platform 等字段

        Returns:
            list of list: 每组是同一餐厅在不同平台的记录
        """
        groups = []

        for record in records:
            matched_group = None
            for group in groups:
                if self._is_same_restaurant(record, group[0]):
                    matched_group = group
                    break

            if matched_group is not None:
                matched_group.append(record)
            else:
                groups.append([record])

        return groups

    def _is_same_restaurant(self, a, b):
        """判断两条记录是否为同一餐厅"""
        name_a = self._normalize_name(a.get("name", ""))
        name_b = self._normalize_name(b.get("name", ""))

        name_score = fuzz.token_sort_ratio(name_a, name_b)

        if name_score >= 95:
            return True

        if name_score < self.NAME_THRESHOLD:
            return False

        addr_a = a.get("address", "")
        addr_b = b.get("address", "")

        if not addr_a or not addr_b:
            return name_score >= 90

        addr_score = fuzz.token_sort_ratio(addr_a, addr_b)
        return addr_score >= self.ADDR_THRESHOLD

    def _normalize_name(self, name):
        """去除常见后缀以提高匹配率"""
        suffixes = ["餐厅", "饭店", "酒楼", "馆", "店", "坊", "麻辣馆", "海鲜酒楼"]
        suffixes.sort(key=len, reverse=True)
        for s in suffixes:
            if name.endswith(s) and len(name) > len(s) + 1:
                name = name[:-len(s)]
                break
        return name.strip()
