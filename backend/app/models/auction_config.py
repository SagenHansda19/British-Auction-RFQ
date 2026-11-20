from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import TriggerType


class AuctionConfig(Base):
    __tablename__ = "auction_configs"
    __table_args__ = (
        CheckConstraint("trigger_window_min > 0", name="trigger_window_positive"),
        CheckConstraint("extension_min > 0", name="extension_positive"),
    )

    rfq_id: Mapped[int] = mapped_column(ForeignKey("rfqs.id", ondelete="CASCADE"), primary_key=True)
    trigger_window_min: Mapped[int] = mapped_column(Integer)
    extension_min: Mapped[int] = mapped_column(Integer)
    trigger: Mapped[TriggerType] = mapped_column(Enum(TriggerType, name="trigger_type"))
