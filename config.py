import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    ES_HOST = os.getenv("ES_HOST", "localhost")
    ES_PORT = int(os.getenv("ES_PORT", 9200))
    ES_INDEX = os.getenv("ES_INDEX", "restaurants")

    BERT_MODEL = os.getenv("BERT_MODEL", "bert-base-chinese")

    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    SCRAPY_CITY = os.getenv("SCRAPY_CITY", "beijing")
    SCRAPY_MAX_PAGES = int(os.getenv("SCRAPY_MAX_PAGES", 10))

    PLATFORMS = os.getenv("PLATFORMS", "dianping,meituan,eleme").split(",")
    SCHEDULER_INTERVAL_HOURS = int(os.getenv("SCHEDULER_INTERVAL_HOURS", 6))
    SQLITE_PATH = os.getenv("SQLITE_PATH", "data/app.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
