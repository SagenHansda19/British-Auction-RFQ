from datetime import date

from sqlalchemy import select

from app.models import AuctionConfig, AuctionEvent, Rfq, User
from app.models.enums import TriggerType, UserRole
from app.services.auction_service import close_expired_auctions
from tests.conftest import at


def make_rfq(db, ref, close, forced="18:30", start="09:00"):
    buyer = db.scalars(select(User)).first() or User(name="Acme", role=UserRole.BUYER)
    db.add(buyer)
    db.flush()
    rfq = Rfq(
        reference_id=ref,
        name=ref,
        buyer_id=buyer.id,
        bid_start_at=at(start),
        original_close_at=at(close),
        current_close_at=at(close),
        forced_close_at=at(forced),
        pickup_date=date(2030, 1, 5),
    )
    db.add(rfq)
    db.flush()
    db.add(
        AuctionConfig(
            rfq_id=rfq.id, trigger_window_min=10, extension_min=5, trigger=TriggerType.ANY_BID
        )
    )
    db.commit()
    return rfq


def test_sweep_closes_only_expired_auctions_and_is_idempotent(db):
    expired = make_rfq(db, "EXPIRED", close="17:00")
    at_forced = make_rfq(db, "AT-FORCED", close="18:00", forced="18:30")
    at_forced.current_close_at = at("18:30")
    still_open = make_rfq(db, "OPEN", close="23:00", forced="23:30")
    db.commit()

    assert close_expired_auctions(db, now=at("18:45")) == 2
    assert expired.status == "CLOSED"
    assert at_forced.status == "FORCE_CLOSED"
    assert still_open.status == "ACTIVE"

    events = db.scalars(select(AuctionEvent).order_by(AuctionEvent.rfq_id)).all()
    assert [(e.rfq_id, str(e.type)) for e in events] == [
        (expired.id, "CLOSED"),
        (at_forced.id, "FORCE_CLOSED"),
    ]
    assert events[0].created_at == at("17:00")

    assert close_expired_auctions(db, now=at("18:45")) == 0


def test_auction_is_not_closed_one_second_early(db):
    make_rfq(db, "EDGE", close="18:00")
    assert close_expired_auctions(db, now=at("17:59")) == 0
    assert close_expired_auctions(db, now=at("18:00")) == 1
