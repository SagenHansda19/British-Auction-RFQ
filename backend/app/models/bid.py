from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Bid(Base):
    __tablename__ = "bids"
    __table_args__ = (
        CheckConstraint("freight_charge >= 0", name="freight_non_negative"),
        CheckConstraint("origin_charge >= 0", name="origin_non_negative"),
        CheckConstraint("destination_charge >= 0", name="destination_non_negative"),
        CheckConstraint(
            "total_price = freight_charge + origin_charge + destination_charge",
            name="total_is_sum",
        ),
        CheckConstraint("transit_time_days >= 0", name="transit_non_negative"),
        Index("ix_bids_rfq_total_created", "rfq_id", "total_price", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rfq_id: Mapped[int] = mapped_column(ForeignKey("rfqs.id", ondelete="CASCADE"))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    carrier_name: Mapped[str] = mapped_column(String(120))

    freight_charge: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    origin_charge: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    destination_charge: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    transit_time_days: Mapped[int] = mapped_column(Integer)
    quote_valid_until: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


Index("ix_bids_rfq_supplier_created", Bid.rfq_id, Bid.supplier_id, Bid.created_at.desc())
