from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.enums import AuctionStatus, EffectiveStatus, TriggerType


@dataclass
class BidInfo:
    id: int
    supplier_id: int
    total_price: Decimal
    created_at: datetime


def rank(latest_bids: list[BidInfo]) -> list[BidInfo]:
    # same price -> earlier bid wins
    return sorted(latest_bids, key=lambda b: (b.total_price, b.created_at, b.id))


def rank_changed(before: list[BidInfo], after: list[BidInfo]) -> bool:
    new_position = {b.supplier_id: i for i, b in enumerate(after)}
    return any(new_position[b.supplier_id] != i for i, b in enumerate(before))


def l1_changed(before: list[BidInfo], after: list[BidInfo]) -> bool:
    old_l1 = before[0].supplier_id if before else None
    new_l1 = after[0].supplier_id if after else None
    return old_l1 != new_l1


def in_trigger_window(now: datetime, close: datetime, window_min: int) -> bool:
    return close - timedelta(minutes=window_min) <= now < close  # [close - X, close)


def trigger_fired(trigger: TriggerType, before: list[BidInfo], after: list[BidInfo]) -> bool:
    if trigger == TriggerType.ANY_BID:
        return True
    if trigger == TriggerType.ANY_RANK_CHANGE:
        return rank_changed(before, after)
    return l1_changed(before, after)


def next_close(close: datetime, forced_close: datetime, extension_min: int) -> datetime:
    return min(close + timedelta(minutes=extension_min), forced_close)


def extension_reason(trigger: TriggerType, window_min: int) -> str:
    reasons = {
        TriggerType.ANY_BID: "Bid received",
        TriggerType.ANY_RANK_CHANGE: "Supplier ranking changed",
        TriggerType.L1_CHANGE: "Lowest bidder (L1) changed",
    }
    return f"{reasons[trigger]} in the last {window_min} minutes"


def terminal_status(close: datetime, forced_close: datetime) -> AuctionStatus:
    return AuctionStatus.FORCE_CLOSED if close >= forced_close else AuctionStatus.CLOSED


def effective_status(
    now: datetime,
    stored_status: AuctionStatus,
    bid_start: datetime,
    close: datetime,
    forced_close: datetime,
) -> EffectiveStatus:
    # db can still say ACTIVE for a few seconds after close, until the sweep runs
    if stored_status != AuctionStatus.ACTIVE:
        return EffectiveStatus(stored_status)
    if now < bid_start:
        return EffectiveStatus.SCHEDULED
    if now >= close:
        return EffectiveStatus(terminal_status(close, forced_close))
    return EffectiveStatus.ACTIVE
