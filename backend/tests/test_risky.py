import pytest
from conftest import make_item


@pytest.mark.parametrize("risky", [True, False])
def test_is_risky_round_trip(client, owner, risky):
    r = client.post("/api/cards", json={"items": [make_item(is_risky=risky)]}, headers=owner)
    assert r.status_code == 201
    assert r.json()["items"][0]["is_risky"] is risky
    listed = client.get("/api/cards", headers=owner).json()["items"]
    assert listed[0]["is_risky"] is risky


@pytest.mark.parametrize("value", ["yes", "true", 1, 0, None])
def test_is_risky_must_be_boolean(client, owner, value):
    r = client.post("/api/cards", json={"items": [make_item(is_risky=value)]}, headers=owner)
    assert r.status_code == 422
    assert r.json()["error"]["fields"] == ["items[0].is_risky"]
    assert client.get("/api/cards", headers=owner).json() == {"items": []}


def test_risky_and_normal_cards_are_both_listed(client, owner):
    items = [make_item(name="생고기", is_risky=True), make_item(name="물", is_risky=False)]
    client.post("/api/cards", json={"items": items}, headers=owner)
    listed = {c["name"]: c["is_risky"] for c in client.get("/api/cards", headers=owner).json()["items"]}
    assert listed == {"생고기": True, "물": False}
