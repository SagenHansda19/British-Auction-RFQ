from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_buyer, get_supplier
from app.core.clock import get_now
from app.db.session import get_db
from app.models import User
from app.models.enums import EffectiveStatus
from app.schemas.bid import BidCreate, PlaceBidResult
from app.schemas.rfq import EventOut, RfqCreate, RfqDetail, RfqOut
from app.services import bid_service, rfq_service

router = APIRouter(prefix="/rfqs", tags=["rfqs"])


@router.post("", response_model=RfqOut, status_code=201)
def create_rfq(
    data: RfqCreate,
    buyer: User = Depends(get_buyer),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
):
    return rfq_service.create_rfq(db, buyer, data, now)


@router.get("", response_model=list[RfqOut])
def list_rfqs(
    status: EffectiveStatus | None = None,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
):
    return rfq_service.list_rfqs(db, now, status)


@router.get("/{rfq_id}", response_model=RfqDetail)
def get_rfq(rfq_id: int, db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    return rfq_service.get_rfq_detail(db, rfq_id, now)


@router.get("/{rfq_id}/events", response_model=list[EventOut])
def list_events(rfq_id: int, db: Session = Depends(get_db)):
    return rfq_service.list_events(db, rfq_id)


@router.post("/{rfq_id}/bids", response_model=PlaceBidResult, status_code=201)
def place_bid(
    rfq_id: int,
    data: BidCreate,
    supplier: User = Depends(get_supplier),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
):
    return bid_service.place_bid(db, rfq_id, supplier, data, now)
