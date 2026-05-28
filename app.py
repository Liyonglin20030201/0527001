import os
import secrets
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS

from config import Config
from query.parser import QueryParser
from query.builder import QueryBuilder
from storage.es_storage import ElasticStorage
from user.db import UserDB
from user.tracker import BehaviorTracker
from user.profile_builder import ProfileBuilder
from user.recommender import PersonalizedRecommender
from monitor.dashboard import monitor_bp, init_monitor


app = Flask(__name__, static_folder="static")
app.secret_key = Config.SECRET_KEY
CORS(app, supports_credentials=True)

app.register_blueprint(monitor_bp)
init_monitor()


@app.route("/")
def index():
    """前端首页"""
    return send_from_directory(app.static_folder, "index.html")

query_parser = QueryParser()
query_builder = QueryBuilder()
storage = ElasticStorage()
user_db = UserDB()
tracker = BehaviorTracker(user_db)
profile_builder = ProfileBuilder(user_db)
recommender = PersonalizedRecommender()


@app.route("/api/recommend", methods=["POST"])
def recommend():
    """智能推荐接口

    接收用户自然语言描述，返回匹配的餐厅列表。
    如果用户已登录，会融入个性化偏好进行重排序。

    Request Body:
        { "query": "想吃辣的安静餐厅，人均100左右" }

    Response:
        {
            "parsed": { ... },
            "results": [ ... ],
            "total": 5,
            "personalized": true/false
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

    personalized = False
    user_id = session.get("user_id")
    if user_id:
        result_ids = [r["id"] for r in results]
        tracker.track_search(user_id, user_query, result_ids)

        profile = profile_builder.build_profile(user_id)
        if profile.get("ready"):
            results = recommender.rerank(results, profile)
            personalized = True

    return jsonify({
        "parsed": parsed,
        "results": results,
        "total": response["hits"]["total"]["value"],
        "personalized": personalized,
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


# ============================
# 用户相关接口
# ============================

@app.route("/api/user/register", methods=["POST"])
def user_register():
    """用户注册（仅需昵称）"""
    data = request.get_json()
    if not data or not data.get("nickname"):
        return jsonify({"error": "请输入昵称"}), 400

    nickname = data["nickname"].strip()
    token = secrets.token_hex(16)

    conn = user_db.get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (nickname, session_token) VALUES (?, ?)",
            (nickname, token),
        )
        conn.commit()
        user_id = cursor.lastrowid
    finally:
        conn.close()

    session["user_id"] = user_id
    session["nickname"] = nickname

    return jsonify({
        "user_id": user_id,
        "nickname": nickname,
        "token": token,
    })


@app.route("/api/user/login", methods=["POST"])
def user_login():
    """用户登录（通过昵称或token）"""
    data = request.get_json()

    conn = user_db.get_connection()
    try:
        if data.get("token"):
            row = conn.execute(
                "SELECT * FROM users WHERE session_token = ?",
                (data["token"],),
            ).fetchone()
        elif data.get("nickname"):
            row = conn.execute(
                "SELECT * FROM users WHERE nickname = ?",
                (data["nickname"],),
            ).fetchone()
        else:
            return jsonify({"error": "请提供昵称或token"}), 400
    finally:
        conn.close()

    if not row:
        return jsonify({"error": "用户不存在"}), 404

    session["user_id"] = row["id"]
    session["nickname"] = row["nickname"]

    return jsonify({
        "user_id": row["id"],
        "nickname": row["nickname"],
    })


@app.route("/api/user/profile", methods=["GET"])
def user_profile():
    """获取当前用户的偏好画像"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "请先登录"}), 401

    profile = profile_builder.build_profile(user_id)
    return jsonify(profile)


@app.route("/api/user/track", methods=["POST"])
def user_track():
    """记录用户行为"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "请先登录"}), 401

    data = request.get_json()
    event_type = data.get("event_type")
    restaurant_id = data.get("restaurant_id")

    if event_type == "click" and restaurant_id:
        tracker.track_click(user_id, restaurant_id)
    elif event_type == "rate" and restaurant_id:
        rating = data.get("rating", 5)
        tracker.track_rating(user_id, restaurant_id, rating)
    else:
        return jsonify({"error": "无效的事件类型"}), 400

    return jsonify({"success": True})


@app.route("/api/user/favorites", methods=["GET"])
def user_favorites():
    """获取收藏列表"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "请先登录"}), 401

    favorites = tracker.get_favorites(user_id)
    return jsonify({"favorites": favorites})


@app.route("/api/user/favorites/<restaurant_id>", methods=["POST"])
def add_favorite(restaurant_id):
    """添加收藏"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "请先登录"}), 401

    tracker.track_favorite(user_id, restaurant_id)
    return jsonify({"success": True})


@app.route("/api/user/favorites/<restaurant_id>", methods=["DELETE"])
def remove_favorite(restaurant_id):
    """取消收藏"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "请先登录"}), 401

    tracker.remove_favorite(user_id, restaurant_id)
    return jsonify({"success": True})


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
