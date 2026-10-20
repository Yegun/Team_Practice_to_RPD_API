import sqlite3
import uuid

from conftest import days_from_today, make_item


def post(client, owner, *items):
    return client.post("/api/cards", json={"items": list(items)}, headers=owner)


def test_list_requires_owner_header(client):
    r = client.get("/api/cards")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "OWNER_MISSING"


def test_list_rejects_non_uuid_owner(client):
    r = client.get("/api/cards", headers={"X-Owner-Id": "not-a-uuid"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "OWNER_MISSING"


def test_empty_list_is_not_an_error(client, owner):
    r = client.get("/api/cards", headers=owner)
    assert r.status_code == 200
    assert r.json() == {"items": []}


def test_create_returns_cards_with_server_fields(client, owner):
    r = post(client, owner, make_item(due_date=days_from_today(5)))
    assert r.status_code == 201
    card = r.json()["items"][0]
    assert uuid.UUID(card["id"])
    assert card["status"] == "remaining"
    assert card["created_at"]
    assert card["days_left"] == 5
    assert card["urgency"] == "ok"
    assert "updated_at" not in card and "owner_id" not in card


def test_created_cards_persist_and_are_listed(client, owner):
    post(client, owner, make_item(name="사과"))
    items = client.get("/api/cards", headers=owner).json()["items"]
    assert [c["name"] for c in items] == ["사과"]


def test_other_owner_cannot_see_cards(client, owner):
    post(client, owner, make_item())
    other = {"X-Owner-Id": str(uuid.uuid4())}
    assert client.get("/api/cards", headers=other).json() == {"items": []}


def test_sort_expired_then_soonest_then_no_due_date_last(client, owner):
    post(
        client,
        owner,
        make_item(name="없음", due_date=None),
        make_item(name="여유", due_date=days_from_today(10)),
        make_item(name="지남", due_date=days_from_today(-2)),
        make_item(name="임박", due_date=days_from_today(1)),
    )
    names = [c["name"] for c in client.get("/api/cards", headers=owner).json()["items"]]
    assert names == ["지남", "임박", "여유", "없음"]


def test_same_due_date_sorted_by_created_order(client, owner):
    d = days_from_today(3)
    post(client, owner, make_item(name="먼저", due_date=d), make_item(name="나중", due_date=d))
    names = [c["name"] for c in client.get("/api/cards", headers=owner).json()["items"]]
    assert names == ["먼저", "나중"]


def test_create_is_all_or_nothing(client, owner):
    r = post(client, owner, make_item(name="좋음"), make_item(quantity=0))
    assert r.status_code == 422
    body = r.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["fields"] == ["items[1].quantity"]
    assert client.get("/api/cards", headers=owner).json() == {"items": []}


def test_create_rejects_empty_items(client, owner):
    r = client.post("/api/cards", json={"items": []}, headers=owner)
    assert r.status_code == 422
    assert r.json()["error"]["fields"] == ["items"]


def test_create_rejects_blank_name_bad_date_bad_quantity(client, owner):
    for field, value in [
        ("name", "   "),
        ("name", "가" * 51),
        ("quantity", "3"),
        ("quantity", 1.5),
        ("due_date", "2026/10/25"),
        ("due_date", "2026-13-40"),
        ("urgent_days", 0),
        ("is_risky", "yes"),
    ]:
        r = post(client, owner, make_item(**{field: value}))
        assert r.status_code == 422, (field, value)
        assert r.json()["error"]["fields"] == [f"items[0].{field}"], (field, value)


def test_create_allows_past_due_date_and_duplicate_names(client, owner):
    r = post(
        client,
        owner,
        make_item(name="우유", due_date=days_from_today(-5)),
        make_item(name="우유"),
    )
    assert r.status_code == 201
    assert r.json()["items"][0]["urgency"] == "expired"


def test_create_requires_owner_header(client):
    r = client.post("/api/cards", json={"items": [make_item()]})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "OWNER_MISSING"


def test_storage_failure_returns_500(client, owner, monkeypatch):
    def boom(*_a, **_k):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr("backend.db.list_remaining", boom)
    r = client.get("/api/cards", headers=owner)
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "STORAGE_ERROR"
