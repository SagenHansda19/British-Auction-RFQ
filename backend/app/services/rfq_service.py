from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import engine
from app.core.errors import AppError, Conflict, NotFound
from app.models import AuctionConfig, AuctionEvent, Bid, Rfq, User
from app.models.enums import EffectiveStatus, EventType
from app.schemas.rfq import AuctionConfigOut, RfqCreate, RfqDetail, RfqOut
from app.services.bid_service import latest_bids, to_bid_out, to_info


def create_rfq(db: Session, buyer: User, data: RfqCreate, now: datetime) -> RfqOut:
    if data.close_at <= now:
        raise AppError("Bid close time must be in the future")

    rfq = Rfq(
        reference_id=data.reference_id,
        name=data.name,
        buyer_id=buyer.id,
        bid_start_at=data.bid_start_at,
        original_close_at=data.close_at,
        current_close_at=data.close_at,
        forced_close_at=data.forced_close_at,
        pickup_date=data.pickup_date,
    )
    db.add(rfq)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise Conflict(f"Reference ID {data.reference_id!r} already exists") from None

    config = AuctionConfig(rfq_id=rfq.id, **data.config.model_dump())
    db.add(config)
    db.commit()
    return get_rfq(db, rfq.id, now)


def summary_query():
    # bids only go down per supplier, so min over all bids = current lowest bid
    return (
        select(Rfq, AuctionConfig, func.min(Bid.total_price), func.count(Bid.id))
        .join(AuctionConfig, AuctionConfig.rfq_id == Rfq.id)
        .outerjoin(Bid, Bid.rfq_id == Rfq.id)
        .group_by(Rfq.id, AuctionConfig.rfq_id)
    )


def to_rfq_out(rfq, config, lowest_bid, bid_count, now: datetime) -> RfqOut:
    return RfqOut(
        id=rfq.id,
        reference_id=rfq.reference_id,
        name=rfq.name,
        buyer_id=rfq.buyer_id,
        bid_start_at=rfq.bid_start_at,
        original_close_at=rfq.original_close_at,
        current_close_at=rfq.current_close_at,
        forced_close_at=rfq.forced_close_at,
        pickup_date=rfq.pickup_date,
        status=engine.effective_status(
            now, rfq.status, rfq.bid_start_at, rfq.current_close_at, rfq.forced_close_at
        ),
        config=AuctionConfigOut.model_validate(config),
        lowest_bid=lowest_bid,
        bid_count=bid_count,
    )


def list_rfqs(db: Session, now: datetime, status: EffectiveStatus | None) -> list[RfqOut]:
    rows = db.execute(summary_query().order_by(Rfq.created_at.desc(), Rfq.id.desc())).all()
    rfqs = [to_rfq_out(*row, now) for row in rows]
    return [r for r in rfqs if status is None or r.status == status]


def get_rfq(db: Session, rfq_id: int, now: datetime) -> RfqOut:
    row = db.execute(summary_query().where(Rfq.id == rfq_id)).first()
    if row is None:
        raise NotFound(f"RFQ {rfq_id} not found")
    return to_rfq_out(*row, now)


def get_rfq_detail(db: Session, rfq_id: int, now: datetime) -> RfqDetail:
    summary = get_rfq(db, rfq_id, now)

    rows = db.execute(
        select(Bid, User.name)
        .join(User, User.id == Bid.supplier_id)
        .where(Bid.rfq_id == rfq_id)
        .order_by(Bid.total_price, Bid.created_at, Bid.id)
    ).all()
    names = {bid.supplier_id: name for bid, name in rows}
    all_bids = [to_bid_out(bid, name) for bid, name in rows]

    latest = {b.id: b for b in latest_bids(db, rfq_id)}
    ranked = engine.rank([to_info(b) for b in latest.values()])
    ranking = [
        to_bid_out(latest[info.id], names[info.supplier_id], rank=position)
        for position, info in enumerate(ranked, start=1)
    ]

    extension_count = db.scalar(
        select(func.count())
        .select_from(AuctionEvent)
        .where(AuctionEvent.rfq_id == rfq_id, AuctionEvent.type == EventType.EXTENDED)
    )
    first_bid = min((bid for bid, _ in rows), key=lambda b: (b.created_at, b.id), default=None)

    return RfqDetail(
        **summary.model_dump(),
        ranking=ranking,
        bids=all_bids,
        extension_count=extension_count,
        starting_price=first_bid.total_price if first_bid else None,
        server_time=now,
    )


def list_events(db: Session, rfq_id: int) -> list[AuctionEvent]:
    if db.get(Rfq, rfq_id) is None:
        raise NotFound(f"RFQ {rfq_id} not found")
    query = (
        select(AuctionEvent)
        .where(AuctionEvent.rfq_id == rfq_id)
        .order_by(AuctionEvent.created_at.desc(), AuctionEvent.id.desc())
    )
    return list(db.scalars(query))
