import uuid

import pytest
from conftest import days_from_today, make_item

from backend import db


def create(client, owner, **overrides) -> dict:
    r = client.post("/api/cards", json={"items": [make_item(**overrides)]}, headers=owner)
    assert r.status_code == 201
    return r.json()["items"][0]


def set_status(client, owner, card_id, status):
    return client.patch(f"/api/cards/{card_id}", json={"status": status}, headers=owner)


def names(client, owner):
    return [c["name"] for c in client.get("/api/cards", headers=owner).json()["items"]]


def db_row(card_id):
    conn = db.connect()
    row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    return row


def test_archive_removes_card_from_list(client, owner):
    keep = create(client, owner, name="남김")
    gone = create(client, owner, name="정리")
    r = set_status(client, owner, gone["id"], "archived")
    assert r.status_code == 200
    assert r.json()["status"] == "archived"
    assert r.json()["id"] == gone["id"]
    assert names(client, owner) == ["남김"]
    assert keep["id"] != gone["id"]


def test_archive_does_not_delete_the_row(client, owner):
    card = create(client, owner, name="우유", quantity=3)
    set_status(client, owner, card["id"], "archived")
    row = db_row(card["id"])
    assert row is not None
    assert row["status"] == "archived" and row["name"] == "우유" and row["quantity"] == 3


def test_archiving_all_cards_gives_empty_list_not_error(client, owner):
    a, b = create(client, owner, name="a"), create(client, owner, name="b")
    set_status(client, owner, a["id"], "archived")
    set_status(client, owner, b["id"], "archived")
    r = client.get("/api/cards", headers=owner)
    assert r.status_code == 200 and r.json() == {"items": []}


def test_archive_twice_is_409_and_unchanged(client, owner):
    card = create(client, owner)
    set_status(client, owner, card["id"], "archived")
    before = db_row(card["id"])["updated_at"]
    r = set_status(client, owner, card["id"], "archived")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CARD_ARCHIVED"
    assert db_row(card["id"])["updated_at"] == before


def test_unarchive_restores_card_to_list_with_same_data(client, owner):
    card = create(client, owner, name="되살림", due_date=days_from_today(2), is_risky=True)
    set_status(client, owner, card["id"], "archived")
    r = set_status(client, owner, card["id"], "remaining")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "remaining"
    assert (body["name"], body["due_date"], body["is_risky"]) == ("되살림", card["due_date"], True)
    assert body["days_left"] == 2
    assert names(client, owner) == ["되살림"]


def test_unarchive_card_that_is_remaining_is_409(client, owner):
    card = create(client, owner)
    r = set_status(client, owner, card["id"], "remaining")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CARD_NOT_ARCHIVED"


def test_archive_unknown_card_is_404(client, owner):
    r = set_status(client, owner, str(uuid.uuid4()), "archived")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "CARD_NOT_FOUND"


def test_cannot_archive_or_unarchive_other_owners_card(client, owner, new_user):
    card = create(client, owner, name="내것")
    other = new_user("bob")
    r = set_status(client, other, card["id"], "archived")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "CARD_NOT_FOUND"
    assert names(client, owner) == ["내것"]

    set_status(client, owner, card["id"], "archived")
    r = set_status(client, other, card["id"], "remaining")
    assert r.status_code == 404
    assert names(client, owner) == []


@pytest.mark.parametrize("status", ["done", "", "ARCHIVED", None, 1])
def test_invalid_status_is_422(client, owner, status):
    card = create(client, owner)
    r = set_status(client, owner, card["id"], status)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert r.json()["error"]["fields"] == ["status"]
    assert names(client, owner) == ["우유"]


def test_status_with_edit_fields_is_422_and_changes_nothing(client, owner):
    card = create(client, owner, name="원래")
    r = client.patch(
        f"/api/cards/{card['id']}", json={"name": "바뀜", "status": "archived"}, headers=owner
    )
    assert r.status_code == 422
    assert names(client, owner) == ["원래"]


def test_archived_card_cannot_be_edited_until_restored(client, owner):
    card = create(client, owner, name="원래")
    set_status(client, owner, card["id"], "archived")
    r = client.patch(f"/api/cards/{card['id']}", json={"name": "x"}, headers=owner)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CARD_ARCHIVED"
    set_status(client, owner, card["id"], "remaining")
    r = client.patch(f"/api/cards/{card['id']}", json={"name": "x"}, headers=owner)
    assert r.status_code == 200


def test_status_change_updates_updated_at(client, owner):
    card = create(client, owner)
    before = db_row(card["id"])["updated_at"]
    set_status(client, owner, card["id"], "archived")
    assert db_row(card["id"])["updated_at"] > before


def test_status_change_requires_login(client, owner):
    card = create(client, owner)
    r = client.patch(f"/api/cards/{card['id']}", json={"status": "archived"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"
    assert names(client, owner) == ["우유"]
