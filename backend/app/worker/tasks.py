from app.core.clock import get_now
from app.db.session import SessionLocal
from app.services.auction_service import close_expired_auctions
from app.worker.celery_app import celery_app


@celery_app.task
def close_expired_auctions_task() -> int:
    with SessionLocal() as db:
        return close_expired_auctions(db, get_now())
