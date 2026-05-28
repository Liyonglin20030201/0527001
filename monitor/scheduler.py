"""APScheduler 定时任务管理"""

import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from config import Config

logger = logging.getLogger(__name__)


class DataScheduler:
    """定时任务管理器

    管理的任务:
    - crawl: 定期运行爬虫抓取新数据
    - analyze: 对新评论做情感分析
    - aggregate: 多平台数据聚合
    - snapshot: 保存数据快照用于趋势检测
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.job_history = []
        self._register_jobs()
        self.scheduler.add_listener(self._on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    def _register_jobs(self):
        interval_hours = Config.SCHEDULER_INTERVAL_HOURS

        self.scheduler.add_job(
            self._job_crawl,
            "interval",
            hours=interval_hours,
            id="crawl",
            name="数据爬取",
            next_run_time=None,
        )
        self.scheduler.add_job(
            self._job_analyze,
            "interval",
            hours=interval_hours,
            id="analyze",
            name="情感分析",
            next_run_time=None,
        )
        self.scheduler.add_job(
            self._job_aggregate,
            "interval",
            hours=interval_hours,
            id="aggregate",
            name="数据聚合",
            next_run_time=None,
        )
        self.scheduler.add_job(
            self._job_snapshot,
            "interval",
            hours=1,
            id="snapshot",
            name="数据快照",
        )

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("调度器已启动")

    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("调度器已关闭")

    def get_jobs(self):
        """获取所有任务状态"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return jobs

    def trigger_job(self, job_id):
        """手动触发某个任务"""
        job = self.scheduler.get_job(job_id)
        if not job:
            return False, f"任务 {job_id} 不存在"

        job.modify(next_run_time=datetime.now())
        return True, f"任务 {job_id} 已触发"

    def get_history(self, limit=20):
        """获取最近的任务执行记录"""
        return self.job_history[-limit:]

    def _on_job_event(self, event):
        """任务执行事件回调"""
        record = {
            "job_id": event.job_id,
            "time": datetime.now().isoformat(),
            "success": event.exception is None,
        }
        if event.exception:
            record["error"] = str(event.exception)
        self.job_history.append(record)
        if len(self.job_history) > 100:
            self.job_history = self.job_history[-50:]

    def _job_crawl(self):
        """定时爬取任务"""
        logger.info("开始执行定时爬取...")
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.project import get_project_settings

        try:
            settings = get_project_settings()
            process = CrawlerProcess(settings)
            for platform in Config.PLATFORMS:
                spider_name = platform
                process.crawl(spider_name, use_mock=True)
            process.start(stop_after_crawl=True)
            logger.info("定时爬取完成")
        except Exception as e:
            logger.error(f"定时爬取失败: {e}")
            raise

    def _job_analyze(self):
        """定时情感分析任务"""
        logger.info("开始执行情感分析...")
        try:
            from sentiment.process import process_reviews
            process_reviews()
            logger.info("情感分析完成")
        except Exception as e:
            logger.error(f"情感分析失败: {e}")
            raise

    def _job_aggregate(self):
        """定时数据聚合任务"""
        logger.info("开始执行数据聚合...")
        try:
            import json
            from aggregator.deduplicator import RestaurantDeduplicator
            from aggregator.merger import DataMerger
            from aggregator.confidence import ConfidenceScorer

            all_records = []
            for platform in Config.PLATFORMS:
                file_path = os.path.join("data", "mock", f"{platform}_restaurants.jsonl")
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                data = json.loads(line)
                                data["source_platform"] = platform
                                all_records.append(data)

            deduplicator = RestaurantDeduplicator()
            groups = deduplicator.deduplicate(all_records)

            merger = DataMerger()
            unified = merger.merge(groups)

            scorer = ConfidenceScorer()
            for record in unified:
                record.confidence_score = scorer.score(record)

            output_path = os.path.join("data", "aggregated_restaurants.jsonl")
            with open(output_path, "w", encoding="utf-8") as f:
                for r in unified:
                    f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

            logger.info(f"数据聚合完成, 输出 {len(unified)} 条记录")
        except Exception as e:
            logger.error(f"数据聚合失败: {e}")
            raise

    def _job_snapshot(self):
        """定时数据快照任务"""
        logger.info("保存数据快照...")
        try:
            from monitor.trend_tracker import TrendTracker
            tracker = TrendTracker()
            tracker.take_snapshot()
            logger.info("数据快照完成")
        except Exception as e:
            logger.error(f"数据快照失败: {e}")
            raise
