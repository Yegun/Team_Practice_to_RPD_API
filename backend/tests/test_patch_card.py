import uuid

import pytest
from conftest import days_from_today, make_item

from backend import db


def create(client, owner, **overrides) -> dict:
    r = client.post("/api/cards", json={"items": [make_item(**overrides)]}, headers=owner)
    assert r.status_code == 201
    return r.json()["items"][0]


def patch(client, owner, card_id, body):
    return client.patch(f"/api/cards/{card_id}", json=body, headers=owner)


def archive_directly(card_id):
    # 정리 API(US-08) 전이라 DB 에 직접 넣어 둔다.
    conn = db.connect()
    conn.execute("UPDATE cards SET status = 'archived' WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()


def test_patch_changes_only_given_fields(client, owner):
    card = create(client, owner, name="우유", quantity=1, storage="fridge")
    r = patch(client, owner, card["id"], {"quantity": 4})
    assert r.status_code == 200
    body = r.json()
    assert body["quantity"] == 4
    assert body["name"] == "우유" and body["storage"] == "fridge"
    assert body["id"] == card["id"] and body["created_at"] == card["created_at"]


def test_patch_all_editable_fields(client, owner):
    card = create(client, owner)
    r = patch(
        client,
        owner,
        card["id"],
        {"name": "생닭", "quantity": 2, "due_date": days_from_today(2),
         "storage": "freezer", "is_risky": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert (body["name"], body["quantity"], body["storage"], body["is_risky"]) == (
        "생닭", 2, "freezer", True,
    )
    assert body["days_left"] == 2


def test_patch_name_is_trimmed(client, owner):
    card = create(client, owner)
    assert patch(client, owner, card["id"], {"name": "  두부  "}).json()["name"] == "두부"


def test_patch_due_date_updates_days_left_urgency_and_order(client, owner):
    a = create(client, owner, name="A", due_date=days_from_today(10))
    create(client, owner, name="B", due_date=days_from_today(5))
    r = patch(client, owner, a["id"], {"due_date": days_from_today(1)})
    assert r.json()["days_left"] == 1
    assert r.json()["urgency"] == "urgent"
    names = [c["name"] for c in client.get("/api/cards", headers=owner).json()["items"]]
    assert names == ["A", "B"]


def test_patch_can_clear_due_date(client, owner):
    card = create(client, owner, due_date=days_from_today(3))
    body = patch(client, owner, card["id"], {"due_date": None}).json()
    assert body["due_date"] is None and body["days_left"] is None
    assert body["urgency"] == "unknown"


def test_patch_does_not_change_urgent_days(client, owner):
    card = create(client, owner, urgent_days=7)
    assert patch(client, owner, card["id"], {"name": "x"}).json()["urgent_days"] == 7


def test_patch_persists(client, owner):
    card = create(client, owner)
    patch(client, owner, card["id"], {"name": "바뀜"})
    assert client.get("/api/cards", headers=owner).json()["items"][0]["name"] == "바뀜"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "   "),
        ("name", "가" * 51),
        ("name", None),
        ("quantity", 0),
        ("quantity", "2"),
        ("quantity", None),
        ("due_date", "2026-02-30"),
        ("due_date", "10/25"),
        ("storage", "attic"),
        ("storage", None),
        ("is_risky", "true"),
        ("is_risky", None),
    ],
)
def test_patch_invalid_value_is_422_with_field(client, owner, field, value):
    card = create(client, owner, name="원래")
    r = patch(client, owner, card["id"], {field: value})
    assert r.status_code == 422, (field, value)
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert r.json()["error"]["fields"] == [field]
    assert client.get("/api/cards", headers=owner).json()["items"][0]["name"] == "원래"


def test_patch_empty_body_is_422(client, owner):
    card = create(client, owner)
    r = patch(client, owner, card["id"], {})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("body", [{"status": "archived"}, {"name": "x", "status": "archived"},
                                  {"urgent_days": 3}, {"id": "x"}])
def test_patch_rejects_status_and_non_editable_fields(client, owner, body):
    card = create(client, owner)
    r = patch(client, owner, card["id"], body)
    assert r.status_code == 422
    assert client.get("/api/cards", headers=owner).json()["items"][0]["status"] == "remaining"


def test_patch_unknown_card_is_404(client, owner):
    r = patch(client, owner, str(uuid.uuid4()), {"name": "x"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "CARD_NOT_FOUND"


def test_patch_other_owners_card_is_404_and_unchanged(client, owner):
    card = create(client, owner, name="내것")
    other = {"X-Owner-Id": str(uuid.uuid4())}
    r = patch(client, other, card["id"], {"name": "빼앗김"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "CARD_NOT_FOUND"
    assert client.get("/api/cards", headers=owner).json()["items"][0]["name"] == "내것"


def test_patch_archived_card_is_409(client, owner):
    card = create(client, owner)
    archive_directly(card["id"])
    r = patch(client, owner, card["id"], {"name": "x"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CARD_ARCHIVED"


def test_patch_requires_owner_header(client, owner):
    card = create(client, owner)
    r = client.patch(f"/api/cards/{card['id']}", json={"name": "x"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "OWNER_MISSING"


def test_patch_updates_updated_at_but_response_hides_it(client, owner):
    card = create(client, owner)
    conn = db.connect()
    before = conn.execute("SELECT updated_at FROM cards WHERE id = ?", (card["id"],)).fetchone()[0]
    r = patch(client, owner, card["id"], {"name": "새이름"})
    after = conn.execute("SELECT updated_at FROM cards WHERE id = ?", (card["id"],)).fetchone()[0]
    conn.close()
    assert after > before
    assert "updated_at" not in r.json()
