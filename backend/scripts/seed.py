from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text

from app.core.clock import get_now
from app.db.session import SessionLocal
from app.models import AuctionConfig, AuctionEvent, Bid, Rfq, User
from app.models.enums import AuctionStatus, EventType, TriggerType, UserRole


def minutes(n):
    return timedelta(minutes=n)


def add_rfq(db, buyer, ref, name, start, close, forced, trigger, status=AuctionStatus.ACTIVE):
    rfq = Rfq(
        reference_id=ref,
        name=name,
        buyer_id=buyer.id,
        bid_start_at=start,
        original_close_at=close,
        current_close_at=close,
        forced_close_at=forced,
        pickup_date=(close + timedelta(days=7)).date(),
        status=status,
    )
    db.add(rfq)
    db.flush()
    db.add(AuctionConfig(rfq_id=rfq.id, trigger_window_min=10, extension_min=5, trigger=trigger))
    return rfq


def add_bid(db, rfq, supplier, carrier, freight, at):
    total = Decimal(freight) + Decimal("1500.00")
    bid = Bid(
        rfq_id=rfq.id,
        supplier_id=supplier.id,
        carrier_name=carrier,
        freight_charge=Decimal(freight),
        origin_charge=Decimal("1000.00"),
        destination_charge=Decimal("500.00"),
        total_price=total,
        transit_time_days=3,
        quote_valid_until=date.today() + timedelta(days=30),
        created_at=at,
    )
    db.add(bid)
    db.flush()
    db.add(
        AuctionEvent(
            rfq_id=rfq.id,
            type=EventType.BID_PLACED,
            supplier_id=supplier.id,
            bid_id=bid.id,
            reason=f"{supplier.name} bid {total} ({carrier})",
            created_at=at,
        )
    )
    return bid


def main():
    now = get_now().replace(second=0, microsecond=0)
    with SessionLocal() as db:
        db.execute(
            text(
                "TRUNCATE users, rfqs, auction_configs, bids, auction_events "
                "RESTART IDENTITY CASCADE"
            )
        )

        buyer = User(name="Acme Logistics", role=UserRole.BUYER)
        s1 = User(name="FastFreight", role=UserRole.SUPPLIER)
        s2 = User(name="QuickShip", role=UserRole.SUPPLIER)
        s3 = User(name="SwiftCargo", role=UserRole.SUPPLIER)
        db.add_all([buyer, s1, s2, s3])
        db.flush()

        add_rfq(
            db,
            buyer,
            "RFQ-1002",
            "Chennai to Pune - 2 trucks",
            now + minutes(60),
            now + minutes(120),
            now + minutes(150),
            TriggerType.ANY_BID,
        )

        closed = add_rfq(
            db,
            buyer,
            "RFQ-0998",
            "Kolkata to Bengaluru - reefer",
            now - minutes(180),
            now - minutes(60),
            now - minutes(30),
            TriggerType.ANY_RANK_CHANGE,
            status=AuctionStatus.CLOSED,
        )
        add_bid(db, closed, s1, "BlueDart", "60000.00", now - minutes(150))
        add_bid(db, closed, s3, "Gati", "58000.00", now - minutes(120))
        db.add(
            AuctionEvent(
                rfq_id=closed.id,
                type=EventType.CLOSED,
                created_at=closed.current_close_at,
                reason="Auction ended at the bid close time",
            )
        )

        forced = add_rfq(
            db,
            buyer,
            "RFQ-0999",
            "Ahmedabad to Jaipur - LTL",
            now - minutes(120),
            now - minutes(70),
            now - minutes(60),
            TriggerType.ANY_BID,
            status=AuctionStatus.FORCE_CLOSED,
        )
        add_bid(db, forced, s2, "Delhivery", "30000.00", now - minutes(100))
        late = add_bid(db, forced, s3, "Gati", "29000.00", now - minutes(75))
        forced.current_close_at = forced.forced_close_at
        db.add(
            AuctionEvent(
                rfq_id=forced.id,
                type=EventType.EXTENDED,
                supplier_id=s3.id,
                bid_id=late.id,
                reason="Bid received in the last 10 minutes",
                old_close_at=now - minutes(70),
                new_close_at=now - minutes(65),
                created_at=now - minutes(75),
            )
        )
        last = add_bid(db, forced, s2, "Delhivery", "28500.00", now - minutes(66))
        db.add(
            AuctionEvent(
                rfq_id=forced.id,
                type=EventType.EXTENDED,
                supplier_id=s2.id,
                bid_id=last.id,
                reason="Bid received in the last 10 minutes",
                old_close_at=now - minutes(65),
                new_close_at=now - minutes(60),
                created_at=now - minutes(66),
            )
        )
        db.add(
            AuctionEvent(
                rfq_id=forced.id,
                type=EventType.FORCE_CLOSED,
                created_at=forced.forced_close_at,
                reason="Auction ended at the forced close time",
            )
        )
        active = add_rfq(
            db,
            buyer,
            "RFQ-1001",
            "Mumbai to Delhi - 20ft container",
            now - minutes(30),
            now + minutes(8),
            now + minutes(30),
            TriggerType.L1_CHANGE,
        )
        add_bid(db, active, s1, "BlueDart", "45000.00", now - minutes(20))
        add_bid(db, active, s2, "Delhivery", "47000.00", now - minutes(15))

        db.commit()
    print("Seeded: 1 buyer, 3 suppliers, 4 RFQs (active, scheduled, closed, force closed)")


if __name__ == "__main__":
    main()
