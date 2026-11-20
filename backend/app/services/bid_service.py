from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app import engine
from app.core.errors import AuctionClosed, AuctionNotStarted, BidNotLower, NotFound
from app.engine import BidInfo
from app.models import AuctionConfig, AuctionEvent, Bid, Rfq, User
from app.models.enums import AuctionStatus, EventType
from app.schemas.bid import BidCreate, BidOut, PlaceBidResult
from app.services.auction_service import close_auction


def place_bid(
    db: Session, rfq_id: int, supplier: User, data: BidCreate, now: datetime
) -> PlaceBidResult:
    # row lock: bids on the same rfq wait here until the previous one commits
    rfq = db.scalars(select(Rfq).where(Rfq.id == rfq_id).with_for_update()).first()
    if rfq is None:
        raise NotFound(f"RFQ {rfq_id} not found")

    if rfq.status != AuctionStatus.ACTIVE:
        raise AuctionClosed("This auction is closed")
    if now >= rfq.current_close_at:
        # celery hasn't closed it yet, do it here
        close_auction(db, rfq)
        db.commit()
        raise AuctionClosed("This auction is closed")
    if now < rfq.bid_start_at:
        raise AuctionNotStarted("Bidding has not started yet")

    total = data.freight_charge + data.origin_charge + data.destination_charge
    total = total.quantize(Decimal("0.01"))
    current = latest_bids(db, rfq.id)
    own_previous = next((b for b in current if b.supplier_id == supplier.id), None)
    if own_previous and total >= own_previous.total_price:
        raise BidNotLower(f"Total must be lower than your last bid ({own_previous.total_price})")

    ranking_before = engine.rank([to_info(b) for b in current])

    bid = Bid(
        rfq_id=rfq.id,
        supplier_id=supplier.id,
        total_price=total,
        created_at=now,
        **data.model_dump(),
    )
    db.add(bid)
    db.flush()
    db.add(
        AuctionEvent(
            rfq_id=rfq.id,
            type=EventType.BID_PLACED,
            supplier_id=supplier.id,
            bid_id=bid.id,
            reason=f"{supplier.name} bid {total} ({data.carrier_name})",
            created_at=now,
        )
    )

    others = [b for b in ranking_before if b.supplier_id != supplier.id]
    ranking_after = engine.rank(others + [to_info(bid)])

    config = db.get(AuctionConfig, rfq.id)
    extended = False
    if engine.in_trigger_window(
        now, rfq.current_close_at, config.trigger_window_min
    ) and engine.trigger_fired(config.trigger, ranking_before, ranking_after):
        new_close = engine.next_close(
            rfq.current_close_at, rfq.forced_close_at, config.extension_min
        )
        # equal means we are already at the forced close
        if new_close > rfq.current_close_at:
            db.add(
                AuctionEvent(
                    rfq_id=rfq.id,
                    type=EventType.EXTENDED,
                    supplier_id=supplier.id,
                    bid_id=bid.id,
                    reason=engine.extension_reason(config.trigger, config.trigger_window_min),
                    old_close_at=rfq.current_close_at,
                    new_close_at=new_close,
                    created_at=now,
                )
            )
            rfq.current_close_at = new_close
            extended = True

    db.commit()
    my_rank = [b.id for b in ranking_after].index(bid.id) + 1
    return PlaceBidResult(
        bid=to_bid_out(bid, supplier.name, rank=my_rank),
        extended=extended,
        current_close_at=rfq.current_close_at,
    )


def latest_bids(db: Session, rfq_id: int) -> list[Bid]:
    query = (
        select(Bid)
        .where(Bid.rfq_id == rfq_id)
        .ext(distinct_on(Bid.supplier_id))
        .order_by(Bid.supplier_id, Bid.created_at.desc(), Bid.id.desc())
    )
    return list(db.scalars(query))


def to_info(bid: Bid) -> BidInfo:
    return BidInfo(
        id=bid.id,
        supplier_id=bid.supplier_id,
        total_price=bid.total_price,
        created_at=bid.created_at,
    )


def to_bid_out(bid: Bid, supplier_name: str, rank: int | None = None) -> BidOut:
    return BidOut(
        id=bid.id,
        rfq_id=bid.rfq_id,
        supplier_id=bid.supplier_id,
        supplier_name=supplier_name,
        carrier_name=bid.carrier_name,
        freight_charge=bid.freight_charge,
        origin_charge=bid.origin_charge,
        destination_charge=bid.destination_charge,
        total_price=bid.total_price,
        transit_time_days=bid.transit_time_days,
        quote_valid_until=bid.quote_valid_until,
        created_at=bid.created_at,
        rank=rank,
    )
