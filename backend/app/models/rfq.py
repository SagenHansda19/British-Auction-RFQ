from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AuctionStatus


class Rfq(Base):
    __tablename__ = "rfqs"
    __table_args__ = (
        CheckConstraint("original_close_at > bid_start_at", name="close_after_start"),
        CheckConstraint("forced_close_at > original_close_at", name="forced_after_close"),
        CheckConstraint(
            "current_close_at >= original_close_at AND current_close_at <= forced_close_at",
            name="current_close_in_bounds",
        ),
        Index(
            "ix_rfqs_active_current_close_at",
            "current_close_at",
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference_id: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    bid_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    original_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    forced_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pickup_date: Mapped[date] = mapped_column(Date)

    status: Mapped[AuctionStatus] = mapped_column(
        Enum(AuctionStatus, name="auction_status"),
        default=AuctionStatus.ACTIVE,
        server_default=AuctionStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
