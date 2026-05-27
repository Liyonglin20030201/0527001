import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from query.parser import QueryParser
from query.builder import QueryBuilder
from storage.es_storage import ElasticStorage


app = Flask(__name__, static_folder="static")
CORS(app)


@app.route("/")
def index():
    """前端首页"""
    return send_from_directory(app.static_folder, "index.html")

query_parser = QueryParser()
query_builder = QueryBuilder()
storage = ElasticStorage()


@app.route("/api/recommend", methods=["POST"])
def recommend():
    """智能推荐接口

    接收用户自然语言描述，返回匹配的餐厅列表。

    Request Body:
        { "query": "想吃辣的安静餐厅，人均100左右" }

    Response:
        {
            "parsed": { ... },
            "results": [ ... ],
            "total": 5
        }
    """
    data = request.get_json()
    if not data or not data.get("query"):
        return jsonify({"error": "请输入您的需求描述"}), 400

    user_query = data["query"].strip()
    parsed = query_parser.parse(user_query)
    es_query = query_builder.build(parsed)

    try:
        response = storage.search(es_query)
    except Exception as e:
        return jsonify({"error": f"搜索服务异常: {str(e)}"}), 500

    results = _format_results(response)

    return jsonify({
        "parsed": parsed,
        "results": results,
        "total": response["hits"]["total"]["value"],
    })


@app.route("/api/restaurant/<doc_id>", methods=["GET"])
def get_restaurant(doc_id):
    """获取餐厅详情"""
    try:
        result = storage.get_restaurant(doc_id)
        return jsonify(result["_source"])
    except Exception as e:
        return jsonify({"error": f"未找到该餐厅: {str(e)}"}), 404


@app.route("/api/health", methods=["GET"])
def health():
    """健康检查"""
    try:
        info = storage.es.info()
        return jsonify({"status": "ok", "elasticsearch": info["version"]["number"]})
    except Exception:
        return jsonify({"status": "degraded", "elasticsearch": "unavailable"})


def _format_results(response):
    """格式化ES搜索结果为前端友好格式"""
    results = []
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        restaurant = {
            "id": hit["_id"],
            "name": source.get("name", ""),
            "address": source.get("address", ""),
            "category": source.get("category", []),
            "avg_price": source.get("avg_price", 0),
            "overall_score": source.get("overall_score", 0),
            "tags": source.get("tags", []),
            "flavor_tags": source.get("flavor_tags", []),
            "atmosphere_tags": source.get("atmosphere_tags", []),
            "recommended_dishes": source.get("recommended_dishes", []),
            "review_count": source.get("review_count", 0),
            "sentiment": source.get("sentiment_summary", {}),
            "top_dishes": _get_top_dishes(source.get("dish_sentiments", [])),
            "match_score": round(hit["_score"], 2),
        }
        results.append(restaurant)
    return results


def _get_top_dishes(dish_sentiments):
    """获取好评率最高的前5道菜"""
    sorted_dishes = sorted(
        dish_sentiments,
        key=lambda x: (x.get("positive_rate", 0), x.get("mention_count", 0)),
        reverse=True,
    )
    return [
        {
            "name": d["dish_name"],
            "positive_rate": d["positive_rate"],
            "mentions": d["mention_count"],
        }
        for d in sorted_dishes[:5]
    ]


if __name__ == "__main__":
    app.run(host=Config.FLASK_HOST, port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)
