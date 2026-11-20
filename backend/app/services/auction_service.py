from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import engine
from app.models import AuctionEvent, Rfq
from app.models.enums import AuctionStatus, EventType


def close_auction(db: Session, rfq: Rfq) -> None:
    rfq.status = engine.terminal_status(rfq.current_close_at, rfq.forced_close_at)
    db.add(
        AuctionEvent(
            rfq_id=rfq.id,
            type=EventType(rfq.status),
            reason="Auction ended at the forced close time"
            if rfq.status == AuctionStatus.FORCE_CLOSED
            else "Auction ended at the bid close time",
            created_at=rfq.current_close_at,
        )
    )


def close_expired_auctions(db: Session, now: datetime) -> int:
    expired = db.scalars(
        select(Rfq)
        .where(Rfq.status == AuctionStatus.ACTIVE, Rfq.current_close_at <= now)
        .with_for_update(skip_locked=True)  # skip rfqs a bid is holding, next run gets them
    ).all()
    for rfq in expired:
        close_auction(db, rfq)
    db.commit()
    return len(expired)
