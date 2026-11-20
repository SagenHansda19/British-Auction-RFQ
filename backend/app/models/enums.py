from enum import StrEnum


class UserRole(StrEnum):
    BUYER = "BUYER"
    SUPPLIER = "SUPPLIER"


class AuctionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    FORCE_CLOSED = "FORCE_CLOSED"


class EffectiveStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    FORCE_CLOSED = "FORCE_CLOSED"


class TriggerType(StrEnum):
    ANY_BID = "ANY_BID"
    ANY_RANK_CHANGE = "ANY_RANK_CHANGE"
    L1_CHANGE = "L1_CHANGE"


class EventType(StrEnum):
    BID_PLACED = "BID_PLACED"
    EXTENDED = "EXTENDED"
    CLOSED = "CLOSED"
    FORCE_CLOSED = "FORCE_CLOSED"
