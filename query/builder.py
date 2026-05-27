"""将解析后的查询条件构建为Elasticsearch DSL"""


class QueryBuilder:
    """将结构化查询条件转为ES查询"""

    def build(self, parsed_query):
        """构建ES查询体

        Args:
            parsed_query: QueryParser.parse() 的输出

        Returns:
            dict: Elasticsearch查询DSL
        """
        must = []
        should = []
        filter_clauses = []

        if parsed_query["flavors"]:
            must.append({
                "terms": {"flavor_tags": parsed_query["flavors"]}
            })

        if parsed_query["atmospheres"]:
            must.append({
                "terms": {"atmosphere_tags": parsed_query["atmospheres"]}
            })

        if parsed_query["categories"]:
            should.append({
                "terms": {"category": parsed_query["categories"], "boost": 2.0}
            })

        if parsed_query["price_range"]:
            low, high = parsed_query["price_range"]
            filter_clauses.append({
                "range": {"avg_price": {"gte": low, "lte": high}}
            })

        keywords = [w for w in parsed_query["keywords"] if len(w) > 1]
        if keywords:
            should.append({
                "multi_match": {
                    "query": " ".join(keywords),
                    "fields": ["name^3", "tags^2", "recommended_dishes^2", "address"],
                    "type": "best_fields",
                }
            })

        if parsed_query["flavors"]:
            for flavor in parsed_query["flavors"]:
                taste_boost = "positive" if flavor != "油腻" else "negative"
                if taste_boost == "positive":
                    should.append({
                        "range": {"sentiment_summary.taste": {"gte": 0.3, "boost": 1.5}}
                    })

        if parsed_query["atmospheres"]:
            should.append({
                "range": {"sentiment_summary.environment": {"gte": 0.3, "boost": 1.5}}
            })

        query_body = {
            "query": {
                "bool": {
                    "must": must,
                    "should": should,
                    "filter": filter_clauses,
                    "minimum_should_match": 1 if should and not must else 0,
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"sentiment_summary.overall": {"order": "desc"}},
                {"overall_score": {"order": "desc"}},
            ],
            "size": 10,
        }

        return query_body
