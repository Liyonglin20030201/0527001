"""监控面板 Flask Blueprint"""

from flask import Blueprint, jsonify, request

from monitor.scheduler import DataScheduler
from monitor.trend_tracker import TrendTracker
from monitor.health_checker import HealthChecker

monitor_bp = Blueprint("monitor", __name__, url_prefix="/api/monitor")

_scheduler = None
_trend_tracker = None
_health_checker = None


def init_monitor(scheduler=None):
    """初始化监控模块"""
    global _scheduler, _trend_tracker, _health_checker
    _scheduler = scheduler or DataScheduler()
    _trend_tracker = TrendTracker()
    _health_checker = HealthChecker()


@monitor_bp.route("/status", methods=["GET"])
def status():
    """系统健康状态"""
    if not _health_checker:
        init_monitor()
    return jsonify(_health_checker.check_all())


@monitor_bp.route("/trends", methods=["GET"])
def trends():
    """热门趋势餐厅"""
    if not _trend_tracker:
        init_monitor()

    days = request.args.get("days", 7, type=int)
    trending = _trend_tracker.get_trending(days=days)

    return jsonify({
        "period_days": days,
        "trending": trending,
        "count": len(trending),
    })


@monitor_bp.route("/jobs", methods=["GET"])
def jobs():
    """定时任务列表"""
    if not _scheduler:
        init_monitor()
    return jsonify({
        "jobs": _scheduler.get_jobs(),
        "history": _scheduler.get_history(limit=10),
    })


@monitor_bp.route("/trigger/<job_id>", methods=["POST"])
def trigger(job_id):
    """手动触发任务"""
    if not _scheduler:
        init_monitor()

    success, message = _scheduler.trigger_job(job_id)
    status_code = 200 if success else 404
    return jsonify({"success": success, "message": message}), status_code
