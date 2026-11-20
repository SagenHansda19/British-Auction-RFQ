from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

MONEY = {"ge": 0, "max_digits": 14, "decimal_places": 2}


class BidCreate(BaseModel):
    carrier_name: str = Field(min_length=1, max_length=120)
    freight_charge: Decimal = Field(**MONEY)
    origin_charge: Decimal = Field(**MONEY)
    destination_charge: Decimal = Field(**MONEY)
    transit_time_days: int = Field(ge=0)
    quote_valid_until: date


class BidOut(BaseModel):
    id: int
    rfq_id: int
    supplier_id: int
    supplier_name: str
    carrier_name: str
    freight_charge: Decimal
    origin_charge: Decimal
    destination_charge: Decimal
    total_price: Decimal
    transit_time_days: int
    quote_valid_until: date
    created_at: datetime
    rank: int | None = None


class PlaceBidResult(BaseModel):
    bid: BidOut
    extended: bool
    current_close_at: datetime
