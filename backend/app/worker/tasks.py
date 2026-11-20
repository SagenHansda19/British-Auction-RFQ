from app.worker.celery_app import celery_app


@celery_app.task
def close_expired_auctions() -> int:
    return 0
