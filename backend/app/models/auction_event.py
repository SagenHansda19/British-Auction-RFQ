from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import EventType


class AuctionEvent(Base):
    __tablename__ = "auction_events"
    __table_args__ = (Index("ix_auction_events_rfq_created", "rfq_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rfq_id: Mapped[int] = mapped_column(ForeignKey("rfqs.id", ondelete="CASCADE"))
    type: Mapped[EventType] = mapped_column(Enum(EventType, name="event_type"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    bid_id: Mapped[int | None] = mapped_column(ForeignKey("bids.id", ondelete="SET NULL"))
    reason: Mapped[str | None] = mapped_column(Text)
    old_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    new_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
