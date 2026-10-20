import pytest
from conftest import make_item


@pytest.mark.parametrize("storage", ["fridge", "freezer", "room"])
def test_allowed_storage_values_round_trip(client, owner, storage):
    r = client.post("/api/cards", json={"items": [make_item(storage=storage)]}, headers=owner)
    assert r.status_code == 201
    assert r.json()["items"][0]["storage"] == storage
    listed = client.get("/api/cards", headers=owner).json()["items"]
    assert listed[0]["storage"] == storage


@pytest.mark.parametrize("storage", ["pantry", "", "FRIDGE", None, 1])
def test_other_storage_values_are_rejected(client, owner, storage):
    r = client.post("/api/cards", json={"items": [make_item(storage=storage)]}, headers=owner)
    assert r.status_code == 422
    assert r.json()["error"]["fields"] == ["items[0].storage"]
    assert client.get("/api/cards", headers=owner).json() == {"items": []}


def test_storage_is_required(client, owner):
    item = make_item()
    del item["storage"]
    r = client.post("/api/cards", json={"items": [item]}, headers=owner)
    assert r.status_code == 422
    assert r.json()["error"]["fields"] == ["items[0].storage"]
