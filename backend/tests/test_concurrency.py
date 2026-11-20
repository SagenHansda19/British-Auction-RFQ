import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.models import AuctionConfig, AuctionEvent, Bid, Rfq, User
from app.models.enums import TriggerType, UserRole
from app.schemas.bid import BidCreate
from app.services import bid_service
from tests.conftest import TestSession, at

N = 20

# window is 60 min so every bid extends by 5 min: 18:00 -> 18:30 in exactly 6 steps.
# without the row lock some bids read the same close time and extensions get lost.


def test_scenario_14_parallel_bids_lose_no_updates(clean_db):
    with TestSession() as db:
        buyer = User(name="Acme", role=UserRole.BUYER)
        suppliers = [User(name=f"S{i}", role=UserRole.SUPPLIER) for i in range(N)]
        db.add_all([buyer, *suppliers])
        db.flush()
        rfq = Rfq(
            reference_id="RFQ-RACE",
            name="Race",
            buyer_id=buyer.id,
            bid_start_at=at("09:00"),
            original_close_at=at("18:00"),
            current_close_at=at("18:00"),
            forced_close_at=at("18:30"),
            pickup_date=date(2030, 1, 5),
        )
        db.add(rfq)
        db.flush()
        db.add(
            AuctionConfig(
                rfq_id=rfq.id, trigger_window_min=60, extension_min=5, trigger=TriggerType.ANY_BID
            )
        )
        db.commit()
        rfq_id, supplier_ids = rfq.id, [s.id for s in suppliers]

    start_together = threading.Barrier(N)

    def one_supplier_bids(index):
        with TestSession() as session:
            supplier = session.get(User, supplier_ids[index])
            data = BidCreate(
                carrier_name="Carrier",
                freight_charge=Decimal(1000 + index),
                origin_charge=Decimal(0),
                destination_charge=Decimal(0),
                transit_time_days=2,
                quote_valid_until=date(2030, 2, 1),
            )
            start_together.wait()
            bid_service.place_bid(session, rfq_id, supplier, data, now=at("17:55"))

    with ThreadPoolExecutor(max_workers=N) as pool:
        for result in [pool.submit(one_supplier_bids, i) for i in range(N)]:
            result.result()

    with TestSession() as db:
        rfq = db.get(Rfq, rfq_id)
        bids = db.scalar(select(func.count()).select_from(Bid))
        placed = db.scalars(select(AuctionEvent).where(AuctionEvent.type == "BID_PLACED")).all()
        extensions = db.scalars(
            select(AuctionEvent)
            .where(AuctionEvent.type == "EXTENDED")
            .order_by(AuctionEvent.old_close_at)
        ).all()

    assert bids == N
    assert len(placed) == N
    assert rfq.current_close_at == at("18:30")
    assert len(extensions) == 6
    assert [(e.old_close_at, e.new_close_at) for e in extensions] == [
        (at("18:00"), at("18:05")),
        (at("18:05"), at("18:10")),
        (at("18:10"), at("18:15")),
        (at("18:15"), at("18:20")),
        (at("18:20"), at("18:25")),
        (at("18:25"), at("18:30")),
    ]
