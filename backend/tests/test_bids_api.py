from datetime import datetime

from sqlalchemy import select

from app.models import AuctionEvent, Rfq
from tests.conftest import at


def make_user(client, name, role):
    return client.post("/api/v1/users", json={"name": name, "role": role}).json()["id"]


def rfq_body(ref="RFQ-1", close="18:00", forced="18:30", trigger="ANY_BID", start="09:00"):
    return {
        "reference_id": ref,
        "name": "Mumbai to Delhi",
        "bid_start_at": at(start).isoformat(),
        "close_at": at(close).isoformat(),
        "forced_close_at": at(forced).isoformat(),
        "pickup_date": "2030-01-05",
        "config": {"trigger_window_min": 10, "extension_min": 5, "trigger": trigger},
    }


def make_rfq(client, buyer, **kwargs):
    response = client.post(
        "/api/v1/rfqs", json=rfq_body(**kwargs), headers={"X-User-Id": str(buyer)}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def bid(client, rfq_id, supplier, total, origin="0", destination="0"):
    body = {
        "carrier_name": "BlueDart",
        "freight_charge": str(total),
        "origin_charge": origin,
        "destination_charge": destination,
        "transit_time_days": 3,
        "quote_valid_until": "2030-01-31",
    }
    return client.post(
        f"/api/v1/rfqs/{rfq_id}/bids", json=body, headers={"X-User-Id": str(supplier)}
    )


def close_time(response):
    return datetime.fromisoformat(response.json()["current_close_at"])


def event_types(db, rfq_id):
    query = select(AuctionEvent.type).where(AuctionEvent.rfq_id == rfq_id).order_by(AuctionEvent.id)
    return [str(t) for t in db.scalars(query)]


def test_create_rfq(client):
    buyer = make_user(client, "Acme", "BUYER")
    response = client.post("/api/v1/rfqs", json=rfq_body(), headers={"X-User-Id": str(buyer)})
    assert response.status_code == 201
    rfq = response.json()
    assert rfq["status"] == "ACTIVE"
    assert rfq["current_close_at"] == rfq["original_close_at"]
    assert rfq["config"] == {"trigger_window_min": 10, "extension_min": 5, "trigger": "ANY_BID"}
    assert rfq["lowest_bid"] is None and rfq["bid_count"] == 0


def test_only_buyers_can_create_rfqs(client):
    supplier = make_user(client, "FastFreight", "SUPPLIER")
    response = client.post("/api/v1/rfqs", json=rfq_body(), headers={"X-User-Id": str(supplier)})
    assert response.status_code == 403


def test_forced_close_must_be_after_close(client):
    buyer = make_user(client, "Acme", "BUYER")
    body = rfq_body(close="18:00", forced="18:00")
    response = client.post("/api/v1/rfqs", json=body, headers={"X-User-Id": str(buyer)})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_reference_id_must_be_unique(client):
    buyer = make_user(client, "Acme", "BUYER")
    make_rfq(client, buyer, ref="RFQ-1")
    response = client.post(
        "/api/v1/rfqs", json=rfq_body(ref="RFQ-1"), headers={"X-User-Id": str(buyer)}
    )
    assert response.status_code == 409


def test_close_time_must_be_in_the_future(client, clock):
    buyer = make_user(client, "Acme", "BUYER")
    clock.now = at("19:00")
    response = client.post("/api/v1/rfqs", json=rfq_body(), headers={"X-User-Id": str(buyer)})
    assert response.status_code == 422


def test_bid_before_start_is_rejected(client):
    buyer, supplier = make_user(client, "Acme", "BUYER"), make_user(client, "S1", "SUPPLIER")
    rfq = make_rfq(client, buyer, start="11:00")
    response = bid(client, rfq, supplier, 100)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "AUCTION_NOT_STARTED"


def test_buyers_cannot_bid(client):
    buyer = make_user(client, "Acme", "BUYER")
    rfq = make_rfq(client, buyer)
    assert bid(client, rfq, buyer, 100).status_code == 403


def test_server_computes_the_total(client):
    buyer, supplier = make_user(client, "Acme", "BUYER"), make_user(client, "S1", "SUPPLIER")
    rfq = make_rfq(client, buyer)
    response = bid(client, rfq, supplier, "1000.50", origin="200.25", destination="99.25")
    assert response.status_code == 201
    assert response.json()["bid"]["total_price"] == "1300.00"
    whole = bid(client, rfq, supplier, 1000)
    assert whole.json()["bid"]["total_price"] == "1000.00"


def test_negative_charges_are_rejected(client):
    buyer, supplier = make_user(client, "Acme", "BUYER"), make_user(client, "S1", "SUPPLIER")
    rfq = make_rfq(client, buyer)
    assert bid(client, rfq, supplier, -5).status_code == 422


def test_scenario_12_bid_must_be_lower_than_own_previous_bid(client):
    buyer, supplier = make_user(client, "Acme", "BUYER"), make_user(client, "S1", "SUPPLIER")
    rfq = make_rfq(client, buyer)
    assert bid(client, rfq, supplier, 100).status_code == 201
    higher = bid(client, rfq, supplier, 150)
    assert higher.status_code == 422
    assert higher.json()["error"]["code"] == "BID_NOT_LOWER"
    assert bid(client, rfq, supplier, 100).status_code == 422
    assert bid(client, rfq, supplier, 90).status_code == 201


def test_a_bid_does_not_have_to_beat_l1(client):
    buyer = make_user(client, "Acme", "BUYER")
    s1, s2 = make_user(client, "S1", "SUPPLIER"), make_user(client, "S2", "SUPPLIER")
    rfq = make_rfq(client, buyer)
    bid(client, rfq, s1, 100)
    assert bid(client, rfq, s2, 500).status_code == 201


def test_scenario_1_bid_before_the_window_does_not_extend(client, clock):
    buyer, supplier = make_user(client, "Acme", "BUYER"), make_user(client, "S1", "SUPPLIER")
    rfq = make_rfq(client, buyer)
    clock.now = at("17:45")
    response = bid(client, rfq, supplier, 100)
    assert response.json()["extended"] is False
    assert close_time(response) == at("18:00")


def test_scenario_2_bid_at_start_of_window_extends(client, clock, db):
    buyer, supplier = make_user(client, "Acme", "BUYER"), make_user(client, "S1", "SUPPLIER")
    rfq = make_rfq(client, buyer)
    clock.now = at("17:50")
    response = bid(client, rfq, supplier, 100)
    assert response.json()["extended"] is True
    assert close_time(response) == at("18:05")

    extension = db.scalars(select(AuctionEvent).where(AuctionEvent.type == "EXTENDED")).one()
    assert extension.old_close_at == at("18:00")
    assert extension.new_close_at == at("18:05")
    assert extension.reason == "Bid received in the last 10 minutes"
    assert event_types(db, rfq) == ["BID_PLACED", "EXTENDED"]


def test_scenario_4_bid_at_close_time_is_rejected_and_auction_closes(client, clock, db):
    buyer, supplier = make_user(client, "Acme", "BUYER"), make_user(client, "S1", "SUPPLIER")
    rfq = make_rfq(client, buyer)
    clock.now = at("18:00")
    response = bid(client, rfq, supplier, 100)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "AUCTION_CLOSED"
    assert db.get(Rfq, rfq).status == "CLOSED"
    assert event_types(db, rfq) == ["CLOSED"]


def test_scenarios_5_and_6_rank_change_trigger(client, clock):
    buyer = make_user(client, "Acme", "BUYER")
    s1, s2, s3 = (make_user(client, n, "SUPPLIER") for n in ("S1", "S2", "S3"))
    rfq = make_rfq(client, buyer, trigger="ANY_RANK_CHANGE")
    bid(client, rfq, s1, 100)
    bid(client, rfq, s2, 200)

    clock.now = at("17:55")
    entered_last = bid(client, rfq, s3, 300)
    assert entered_last.json()["extended"] is False

    overtook = bid(client, rfq, s2, 90)
    assert overtook.json()["extended"] is True
    assert entered_last.json()["bid"]["rank"] == 3
    assert overtook.json()["bid"]["rank"] == 1
    assert close_time(overtook) == at("18:05")


def test_scenarios_7_and_8_l1_change_trigger(client, clock):
    buyer = make_user(client, "Acme", "BUYER")
    s1, s2, s3 = (make_user(client, n, "SUPPLIER") for n in ("S1", "S2", "S3"))
    rfq = make_rfq(client, buyer, trigger="L1_CHANGE")
    bid(client, rfq, s1, 100)
    bid(client, rfq, s2, 200)
    bid(client, rfq, s3, 300)

    clock.now = at("17:55")
    became_l2 = bid(client, rfq, s3, 150)
    assert became_l2.json()["extended"] is False

    became_l1 = bid(client, rfq, s2, 90)
    assert became_l1.json()["extended"] is True


def test_scenarios_10_and_11_extension_stops_at_forced_close(client, clock, db):
    buyer = make_user(client, "Acme", "BUYER")
    s1, s2 = make_user(client, "S1", "SUPPLIER"), make_user(client, "S2", "SUPPLIER")
    rfq = make_rfq(client, buyer, close="18:28", forced="18:30")

    clock.now = at("18:25")
    first = bid(client, rfq, s1, 100)
    assert first.json()["extended"] is True
    assert close_time(first) == at("18:30")

    clock.now = at("18:26")
    second = bid(client, rfq, s2, 90)
    assert second.status_code == 201
    assert second.json()["extended"] is False
    assert event_types(db, rfq).count("EXTENDED") == 1

    clock.now = at("18:30")
    assert bid(client, rfq, s1, 80).status_code == 409
    db.expire_all()
    assert db.get(Rfq, rfq).status == "FORCE_CLOSED"
