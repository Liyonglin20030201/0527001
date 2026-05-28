"""个性化推荐重排序"""


class PersonalizedRecommender:
    """将用户画像融入搜索结果排序

    策略: final_score = (1 - PROFILE_WEIGHT) * match_score + PROFILE_WEIGHT * profile_match
    冷启动时不做个性化，直接返回原始结果。
    """

    PROFILE_WEIGHT = 0.3

    def rerank(self, results, user_profile):
        """对搜索结果进行个性化重排序

        Args:
            results: list of dict, ES搜索结果(已格式化)
            user_profile: dict, 用户画像 (来自 ProfileBuilder.build_profile)

        Returns:
            list of dict: 重排序后的结果
        """
        if not user_profile or not user_profile.get("ready"):
            return results

        for r in results:
            profile_score = self._compute_profile_match(r, user_profile)
            original_score = r.get("match_score", 0)
            r["personalized_score"] = round(
                (1 - self.PROFILE_WEIGHT) * original_score
                + self.PROFILE_WEIGHT * profile_score * original_score,
                2,
            )
            r["profile_match"] = round(profile_score, 3)

        results.sort(key=lambda x: x.get("personalized_score", 0), reverse=True)
        return results

    def _compute_profile_match(self, restaurant, profile):
        """计算餐厅与用户画像的匹配度 (0-1)"""
        scores = []

        flavor_prefs = profile.get("flavor_preferences", {})
        if flavor_prefs:
            restaurant_flavors = restaurant.get("flavor_tags", [])
            flavor_match = self._tag_match_score(restaurant_flavors, flavor_prefs)
            scores.append(flavor_match)

        atm_prefs = profile.get("atmosphere_preferences", {})
        if atm_prefs:
            restaurant_atm = restaurant.get("atmosphere_tags", [])
            atm_match = self._tag_match_score(restaurant_atm, atm_prefs)
            scores.append(atm_match)

        cat_prefs = profile.get("category_preferences", {})
        if cat_prefs:
            restaurant_cats = restaurant.get("category", [])
            cat_match = self._tag_match_score(restaurant_cats, cat_prefs)
            scores.append(cat_match)

        price_range = profile.get("price_range", [0, 200])
        restaurant_price = restaurant.get("avg_price", 0)
        if restaurant_price and price_range[1] > price_range[0]:
            price_match = self._price_match_score(restaurant_price, price_range)
            scores.append(price_match)

        if not scores:
            return 0.5

        return sum(scores) / len(scores)

    def _tag_match_score(self, restaurant_tags, preference_dict):
        """标签匹配度: 餐厅的标签在用户偏好中的加权得分"""
        if not restaurant_tags or not preference_dict:
            return 0.0

        total = 0.0
        for tag in restaurant_tags:
            if tag in preference_dict:
                total += preference_dict[tag]

        max_possible = sum(sorted(preference_dict.values(), reverse=True)[:len(restaurant_tags)])
        if max_possible == 0:
            return 0.0
        return min(total / max_possible, 1.0)

    def _price_match_score(self, price, price_range):
        """价格匹配度: 在偏好范围内为1.0，偏离越远越低"""
        low, high = price_range
        if low <= price <= high:
            return 1.0
        if price < low:
            distance = (low - price) / max(low, 1)
        else:
            distance = (price - high) / max(high, 1)
        return max(0.0, 1.0 - distance)
