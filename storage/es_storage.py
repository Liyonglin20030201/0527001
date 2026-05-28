from elasticsearch import Elasticsearch
from config import Config


RESTAURANT_MAPPING = {
    "mappings": {
        "properties": {
            "name": {"type": "text", "analyzer": "ik_max_word", "fields": {"keyword": {"type": "keyword"}}},
            "address": {"type": "text", "analyzer": "ik_max_word"},
            "phone": {"type": "keyword"},
            "category": {"type": "keyword"},
            "avg_price": {"type": "float"},
            "overall_score": {"type": "float"},
            "url": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "recommended_dishes": {"type": "keyword"},
            "sentiment_summary": {
                "type": "object",
                "properties": {
                    "overall": {"type": "float"},
                    "taste": {"type": "float"},
                    "environment": {"type": "float"},
                    "service": {"type": "float"},
                    "price": {"type": "float"},
                },
            },
            "dish_sentiments": {
                "type": "nested",
                "properties": {
                    "dish_name": {"type": "text", "analyzer": "ik_max_word", "fields": {"keyword": {"type": "keyword"}}},
                    "positive_rate": {"type": "float"},
                    "mention_count": {"type": "integer"},
                    "sample_reviews": {"type": "text", "analyzer": "ik_max_word"},
                },
            },
            "review_count": {"type": "integer"},
            "flavor_tags": {"type": "keyword"},
            "atmosphere_tags": {"type": "keyword"},
            "source_platforms": {"type": "keyword"},
            "confidence_score": {"type": "float"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "ik_max_word": {
                    "type": "custom",
                    "tokenizer": "ik_max_word",
                }
            }
        },
    },
}


class ElasticStorage:
    """Elasticsearch 存储管理器"""

    def __init__(self):
        self.es = Elasticsearch(
            [{"host": Config.ES_HOST, "port": Config.ES_PORT, "scheme": "http"}]
        )
        self.index = Config.ES_INDEX

    def create_index(self):
        """创建索引，如已存在则跳过"""
        if not self.es.indices.exists(index=self.index):
            self.es.indices.create(index=self.index, body=RESTAURANT_MAPPING)
            return True
        return False

    def delete_index(self):
        """删除索引"""
        if self.es.indices.exists(index=self.index):
            self.es.indices.delete(index=self.index)

    def index_restaurant(self, doc, doc_id=None):
        """索引单个餐厅文档"""
        self.es.index(index=self.index, id=doc_id, document=doc)

    def bulk_index(self, docs):
        """批量索引餐厅文档"""
        actions = []
        for doc in docs:
            action = {"index": {"_index": self.index}}
            if "id" in doc:
                action["index"]["_id"] = doc.pop("id")
            actions.append(action)
            actions.append(doc)

        if actions:
            self.es.bulk(operations=actions, refresh=True)

    def search(self, query_body):
        """执行搜索"""
        return self.es.search(index=self.index, body=query_body)

    def get_restaurant(self, doc_id):
        """获取单个餐厅文档"""
        return self.es.get(index=self.index, id=doc_id)

    def search_by_tags(self, categories=None, flavor_tags=None, atmosphere_tags=None,
                       price_range=None, exclude_ids=None, size=10):
        """按标签组合搜索餐厅（用于猜你喜欢和相似推荐）"""
        must = []
        should = []
        filter_clauses = []

        if categories:
            should.append({"terms": {"category": categories, "boost": 2.0}})
        if flavor_tags:
            should.append({"terms": {"flavor_tags": flavor_tags, "boost": 1.5}})
        if atmosphere_tags:
            should.append({"terms": {"atmosphere_tags": atmosphere_tags, "boost": 1.5}})
        if price_range:
            filter_clauses.append({
                "range": {"avg_price": {"gte": price_range[0], "lte": price_range[1]}}
            })

        must_not = []
        if exclude_ids:
            must_not.append({"ids": {"values": exclude_ids}})

        if not should:
            should.append({"match_all": {}})

        query_body = {
            "query": {
                "bool": {
                    "must": must,
                    "should": should,
                    "filter": filter_clauses,
                    "must_not": must_not,
                    "minimum_should_match": 1 if should else 0,
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"overall_score": {"order": "desc"}},
            ],
            "size": size,
        }
        return self.search(query_body)

    def find_similar(self, doc_id, size=5):
        """基于 more_like_this 查找相似餐厅"""
        query_body = {
            "query": {
                "bool": {
                    "must": [{
                        "more_like_this": {
                            "fields": ["tags", "category", "flavor_tags", "atmosphere_tags", "name"],
                            "like": [{"_index": self.index, "_id": doc_id}],
                            "min_term_freq": 1,
                            "min_doc_freq": 1,
                            "max_query_terms": 20,
                        }
                    }],
                    "must_not": [{"ids": {"values": [doc_id]}}],
                }
            },
            "size": size,
        }
        return self.search(query_body)

    def get_top_rated(self, size=10, min_score=4.0):
        """获取高评分餐厅"""
        query_body = {
            "query": {
                "range": {"overall_score": {"gte": min_score}}
            },
            "sort": [
                {"overall_score": {"order": "desc"}},
                {"review_count": {"order": "desc"}},
            ],
            "size": size,
        }
        return self.search(query_body)
