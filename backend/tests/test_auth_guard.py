import uuid

import pytest

from conftest import make_item

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


def create(client, headers, **overrides) -> dict:
    r = client.post("/api/cards", json={"items": [make_item(**overrides)]}, headers=headers)
    assert r.status_code == 201
    return r.json()["items"][0]


def names(client, headers):
    return [c["name"] for c in client.get("/api/cards", headers=headers).json()["items"]]


PROTECTED = [
    ("get", "/api/cards", {}),
    ("post", "/api/cards", {"json": {"items": [make_item()]}}),
    ("patch", f"/api/cards/{uuid.uuid4()}", {"json": {"name": "x"}}),
    ("patch", f"/api/cards/{uuid.uuid4()}", {"json": {"status": "archived"}}),
    ("patch", f"/api/cards/{uuid.uuid4()}", {"json": {"status": "remaining"}}),
    ("post", "/api/receipts/analyze", {"files": {"image": ("a.jpg", JPEG, "image/jpeg")}}),
]


@pytest.mark.parametrize("method,path,kwargs", PROTECTED)
def test_every_card_api_returns_401_without_login(client, method, path, kwargs):
    r = getattr(client, method)(path, **kwargs)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize(
    "method,path,kwargs",
    [
        ("post", "/api/cards", {"json": {"items": []}}),
        ("patch", f"/api/cards/{uuid.uuid4()}", {"json": {}}),
        ("post", "/api/receipts/analyze", {}),
    ],
)
def test_401_comes_before_validation_and_lookup(client, method, path, kwargs):
    r = getattr(client, method)(path, **kwargs)
    assert r.status_code == 401


def test_expired_or_logged_out_session_is_401_on_cards(client, new_user):
    client.post("/api/auth/signup", json={"login_id": "carol", "password": "password-1234"})
    client.post("/api/auth/logout")
    assert client.get("/api/cards").status_code == 401


def test_health_stays_open(client):
    assert client.get("/api/health").status_code == 200


def test_other_users_card_is_404_and_unchanged(client, owner, new_user):
    bob = new_user("bob")
    card = create(client, owner, name="내것")
    for body in ({"name": "빼앗김"}, {"status": "archived"}):
        r = client.patch(f"/api/cards/{card['id']}", json=body, headers=bob)
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "CARD_NOT_FOUND"
    # 없는 카드와 같은 응답이다.
    missing = client.patch(f"/api/cards/{uuid.uuid4()}", json={"name": "x"}, headers=bob)
    assert missing.json() == r.json()
    assert names(client, owner) == ["내것"]


def test_lists_never_mix_users(client, owner, new_user):
    bob = new_user("bob")
    create(client, owner, name="앨리스 우유")
    create(client, bob, name="밥 사과")
    assert names(client, owner) == ["앨리스 우유"]
    assert names(client, bob) == ["밥 사과"]


def test_new_card_belongs_to_logged_in_user_not_body(client, owner, new_user, tmp_path):
    import sqlite3

    bob = new_user("bob")
    r = client.post(
        "/api/cards",
        json={"items": [{**make_item(), "owner_id": "someone-else"}]},
        headers=bob,
    )
    assert r.status_code == 422  # 본문에 소유자 값을 받지 않는다.
    card = create(client, owner)
    row = sqlite3.connect(tmp_path / "test.db").execute(
        "SELECT owner_id FROM cards WHERE id = ?", (card["id"],)
    ).fetchone()
    alice_id = sqlite3.connect(tmp_path / "test.db").execute(
        "SELECT id FROM users WHERE login_id = 'alice'"
    ).fetchone()
    assert row == alice_id


def test_migrated_users_cards_are_visible_only_to_claimant(client, tmp_path, new_user):
    import sqlite3

    from backend.db import connect

    connect().close()
    conn = sqlite3.connect(tmp_path / "test.db")
    conn.execute("INSERT INTO users VALUES ('mig', 'migrated@test.com', '', 't')")
    conn.execute(
        "INSERT INTO cards VALUES ('c1','mig','옛 우유',1,NULL,'fridge',0,3,'remaining','t','t')"
    )
    conn.commit()

    other = new_user("dave")
    assert names(client, other) == []
    claimed = new_user("migrated@test.com")
    assert names(client, claimed) == ["옛 우유"]
