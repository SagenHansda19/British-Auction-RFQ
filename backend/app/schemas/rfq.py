from datetime import date, datetime
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.models.enums import EffectiveStatus, EventType, TriggerType
from app.schemas.bid import BidOut


class AuctionConfigIn(BaseModel):
    trigger_window_min: int = Field(gt=0)
    extension_min: int = Field(gt=0)
    trigger: TriggerType


class AuctionConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trigger_window_min: int
    extension_min: int
    trigger: TriggerType


class RfqCreate(BaseModel):
    reference_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    bid_start_at: AwareDatetime
    close_at: AwareDatetime
    forced_close_at: AwareDatetime
    pickup_date: date
    config: AuctionConfigIn

    @model_validator(mode="after")
    def check_times(self):
        if self.close_at <= self.bid_start_at:
            raise ValueError("Bid close time must be after bid start time")
        if self.forced_close_at <= self.close_at:
            raise ValueError("Forced close time must be after bid close time")
        return self


class RfqOut(BaseModel):
    id: int
    reference_id: str
    name: str
    buyer_id: int
    bid_start_at: datetime
    original_close_at: datetime
    current_close_at: datetime
    forced_close_at: datetime
    pickup_date: date
    status: EffectiveStatus
    config: AuctionConfigOut
    lowest_bid: Decimal | None
    bid_count: int


class RfqDetail(RfqOut):
    ranking: list[BidOut]
    bids: list[BidOut]
    extension_count: int
    starting_price: Decimal | None
    server_time: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: EventType
    supplier_id: int | None
    bid_id: int | None
    reason: str | None
    old_close_at: datetime | None
    new_close_at: datetime | None
    created_at: datetime
