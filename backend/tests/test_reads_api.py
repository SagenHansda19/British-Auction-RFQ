from tests.conftest import at
from tests.test_bids_api import bid, make_rfq, make_user


def setup_auction(client, clock):
    buyer = make_user(client, "Acme", "BUYER")
    s1, s2, s3 = (make_user(client, n, "SUPPLIER") for n in ("S1", "S2", "S3"))
    rfq = make_rfq(client, buyer)
    clock.now = at("17:00")
    bid(client, rfq, s1, 500)
    bid(client, rfq, s2, 400)
    bid(client, rfq, s3, 450)
    clock.now = at("17:55")
    bid(client, rfq, s2, 300)
    return rfq, (s1, s2, s3)


def test_listing_shows_lowest_bid_close_times_and_status(client, clock):
    rfq, _ = setup_auction(client, clock)
    [row] = client.get("/api/v1/rfqs").json()
    assert row["id"] == rfq
    assert row["reference_id"] == "RFQ-1"
    assert row["lowest_bid"] == "300.00"
    assert row["bid_count"] == 4
    assert row["current_close_at"] == "2030-01-01T18:05:00Z"
    assert row["forced_close_at"] == "2030-01-01T18:30:00Z"
    assert row["status"] == "ACTIVE"


def test_listing_status_filter_uses_the_clock(client, clock):
    setup_auction(client, clock)
    assert len(client.get("/api/v1/rfqs?status=ACTIVE").json()) == 1
    clock.now = at("18:05")
    assert client.get("/api/v1/rfqs?status=ACTIVE").json() == []
    assert len(client.get("/api/v1/rfqs?status=CLOSED").json()) == 1


def test_details_ranking_all_bids_config_and_metrics(client, clock):
    rfq, (s1, s2, s3) = setup_auction(client, clock)
    detail = client.get(f"/api/v1/rfqs/{rfq}").json()

    ranking = [(b["rank"], b["supplier_name"], b["total_price"]) for b in detail["ranking"]]
    assert ranking == [(1, "S2", "300.00"), (2, "S3", "450.00"), (3, "S1", "500.00")]

    all_prices = [b["total_price"] for b in detail["bids"]]
    assert all_prices == ["300.00", "400.00", "450.00", "500.00"]
    assert detail["bids"][0]["quote_valid_until"] == "2030-01-31"

    assert detail["config"] == {"trigger_window_min": 10, "extension_min": 5, "trigger": "ANY_BID"}
    assert detail["extension_count"] == 1
    assert detail["starting_price"] == "500.00"
    assert detail["server_time"] == "2030-01-01T17:55:00Z"


def test_activity_log_is_newest_first_with_extension_reason(client, clock):
    rfq, _ = setup_auction(client, clock)
    events = client.get(f"/api/v1/rfqs/{rfq}/events").json()
    assert [e["type"] for e in events] == [
        "EXTENDED",
        "BID_PLACED",
        "BID_PLACED",
        "BID_PLACED",
        "BID_PLACED",
    ]
    extension = events[0]
    assert extension["reason"] == "Bid received in the last 10 minutes"
    assert extension["old_close_at"] == "2030-01-01T18:00:00Z"
    assert extension["new_close_at"] == "2030-01-01T18:05:00Z"


def test_unknown_rfq_is_404(client):
    assert client.get("/api/v1/rfqs/999").status_code == 404
    assert client.get("/api/v1/rfqs/999/events").status_code == 404
