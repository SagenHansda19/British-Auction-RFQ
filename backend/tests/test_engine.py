from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app import engine
from app.engine import BidInfo
from app.models.enums import AuctionStatus, EffectiveStatus, TriggerType


def t(hhmm: str, seconds: int = 0) -> datetime:
    hour, minute = map(int, hhmm.split(":"))
    return datetime(2026, 1, 1, hour, minute, seconds, tzinfo=UTC)


def bid(bid_id: int, supplier_id: int, price: str, at: str = "17:00") -> BidInfo:
    return BidInfo(id=bid_id, supplier_id=supplier_id, total_price=Decimal(price), created_at=t(at))


CLOSE, FORCED, X, Y = t("18:00"), t("18:30"), 10, 5


def test_rank_orders_by_lowest_price():
    ranked = engine.rank([bid(1, 1, "300"), bid(2, 2, "100"), bid(3, 3, "200")])
    assert [b.supplier_id for b in ranked] == [2, 3, 1]


def test_scenario_13_equal_totals_earlier_bid_ranks_higher():
    ranked = engine.rank([bid(1, 1, "100", at="17:10"), bid(2, 2, "100", at="17:05")])
    assert [b.supplier_id for b in ranked] == [2, 1]


def test_rank_of_no_bids_is_empty():
    assert engine.rank([]) == []


def test_scenario_5_new_supplier_entering_last_is_not_a_rank_change():
    before = engine.rank([bid(1, 1, "100"), bid(2, 2, "200")])
    after = engine.rank([bid(1, 1, "100"), bid(2, 2, "200"), bid(3, 3, "300")])
    assert engine.rank_changed(before, after) is False


def test_new_supplier_entering_ahead_is_a_rank_change():
    before = engine.rank([bid(1, 1, "100"), bid(2, 2, "200")])
    after = engine.rank([bid(1, 1, "100"), bid(2, 2, "200"), bid(3, 3, "150")])
    assert engine.rank_changed(before, after) is True


def test_scenario_6_s2_overtakes_s1_is_a_rank_change():
    before = engine.rank([bid(1, 1, "100"), bid(2, 2, "200")])
    after = engine.rank([bid(1, 1, "100"), bid(3, 2, "90")])
    assert engine.rank_changed(before, after) is True


def test_lowering_price_without_changing_order_is_not_a_rank_change():
    before = engine.rank([bid(1, 1, "100"), bid(2, 2, "200")])
    after = engine.rank([bid(1, 1, "100"), bid(3, 2, "150")])
    assert engine.rank_changed(before, after) is False


def test_scenario_7_s3_becoming_l2_is_not_an_l1_change():
    before = engine.rank([bid(1, 1, "100"), bid(2, 2, "200"), bid(3, 3, "300")])
    after = engine.rank([bid(1, 1, "100"), bid(2, 2, "200"), bid(4, 3, "150")])
    assert engine.l1_changed(before, after) is False
    assert engine.rank_changed(before, after) is True


def test_scenario_8_s2_beating_s1_is_an_l1_change():
    before = engine.rank([bid(1, 1, "100"), bid(2, 2, "200")])
    after = engine.rank([bid(1, 1, "100"), bid(3, 2, "90")])
    assert engine.l1_changed(before, after) is True


def test_very_first_bid_is_an_l1_change():
    assert engine.l1_changed([], engine.rank([bid(1, 1, "100")])) is True


def test_scenario_1_bid_at_1745_is_outside_the_window():
    assert engine.in_trigger_window(t("17:45"), CLOSE, X) is False


def test_scenario_2_bid_at_exactly_1750_is_inside_the_window():
    assert engine.in_trigger_window(t("17:50"), CLOSE, X) is True


def test_scenario_3_bid_at_1755_is_inside_the_window():
    assert engine.in_trigger_window(t("17:55"), CLOSE, X) is True


def test_scenario_4_bid_at_exactly_1800_is_outside_the_window_and_auction_is_closed():
    assert engine.in_trigger_window(t("18:00"), CLOSE, X) is False
    status = engine.effective_status(t("18:00"), AuctionStatus.ACTIVE, t("10:00"), CLOSE, FORCED)
    assert status == EffectiveStatus.CLOSED


def test_any_bid_trigger_always_fires():
    same = engine.rank([bid(1, 1, "100")])
    assert engine.trigger_fired(TriggerType.ANY_BID, same, same) is True


def test_rank_change_trigger_uses_rank_changed():
    before = engine.rank([bid(1, 1, "100"), bid(2, 2, "200")])
    entered_last = engine.rank([bid(1, 1, "100"), bid(2, 2, "200"), bid(3, 3, "300")])
    overtook = engine.rank([bid(1, 1, "100"), bid(4, 2, "90")])
    assert engine.trigger_fired(TriggerType.ANY_RANK_CHANGE, before, entered_last) is False
    assert engine.trigger_fired(TriggerType.ANY_RANK_CHANGE, before, overtook) is True


def test_l1_change_trigger_uses_l1_changed():
    before = engine.rank([bid(1, 1, "100"), bid(2, 2, "200"), bid(3, 3, "300")])
    new_l2 = engine.rank([bid(1, 1, "100"), bid(2, 2, "200"), bid(4, 3, "150")])
    new_l1 = engine.rank([bid(1, 1, "100"), bid(2, 2, "200"), bid(4, 3, "50")])
    assert engine.trigger_fired(TriggerType.L1_CHANGE, before, new_l2) is False
    assert engine.trigger_fired(TriggerType.L1_CHANGE, before, new_l1) is True


def test_scenario_3_extension_adds_y_to_the_close_not_to_the_bid_time():
    assert engine.next_close(CLOSE, FORCED, Y) == t("18:05")


def test_scenario_9_repeated_triggers_extend_until_the_forced_close():
    close, history = CLOSE, []
    for _ in range(8):
        bid_time = close - timedelta(minutes=1)
        if engine.in_trigger_window(bid_time, close, X):
            close = engine.next_close(close, FORCED, Y)
        history.append(close.strftime("%H:%M"))
    assert history == ["18:05", "18:10", "18:15", "18:20", "18:25", "18:30", "18:30", "18:30"]


def test_scenario_10_extension_is_capped_at_the_forced_close():
    assert engine.next_close(t("18:28"), FORCED, Y) == t("18:30")


def test_scenario_11_at_the_forced_close_there_is_nothing_to_extend():
    assert engine.next_close(FORCED, FORCED, Y) == FORCED


def test_terminal_status():
    assert engine.terminal_status(t("18:05"), FORCED) == AuctionStatus.CLOSED
    assert engine.terminal_status(FORCED, FORCED) == AuctionStatus.FORCE_CLOSED


def test_effective_status_through_the_lifecycle():
    start = t("10:00")

    def status_at(now, stored=AuctionStatus.ACTIVE, close=CLOSE):
        return engine.effective_status(now, stored, start, close, FORCED)

    assert status_at(t("09:59")) == EffectiveStatus.SCHEDULED
    assert status_at(t("10:00")) == EffectiveStatus.ACTIVE
    assert status_at(t("17:59")) == EffectiveStatus.ACTIVE
    assert status_at(t("18:00")) == EffectiveStatus.CLOSED
    assert status_at(t("18:31"), close=FORCED) == EffectiveStatus.FORCE_CLOSED
    assert status_at(t("12:00"), stored=AuctionStatus.CLOSED) == EffectiveStatus.CLOSED
