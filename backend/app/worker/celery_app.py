from celery import Celery

from app.core.config import settings

celery_app = Celery("rfq", broker=settings.redis_url, include=["app.worker.tasks"])

celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "close-expired-auctions": {
        "task": "app.worker.tasks.close_expired_auctions_task",
        "schedule": 5.0,
    },
}
