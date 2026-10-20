import pytest

from backend.ai import get_analyzer
from backend.main import app

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 64
GIF = b"GIF89a" + b"\x00" * 64

URL = "/api/receipts/analyze"


def upload(client, owner, data: bytes, name="receipt.jpg", ctype="image/jpeg"):
    return client.post(URL, files={"image": (name, data, ctype)}, headers=owner)


def assert_error(r, status, code):
    assert r.status_code == status, r.text
    assert r.json()["error"]["code"] == code


@pytest.mark.parametrize(
    ("data", "name", "ctype"),
    [(JPEG, "a.jpg", "image/jpeg"), (PNG, "a.png", "image/png"), (WEBP, "a.webp", "image/webp")],
)
def test_allowed_images_return_drafts(client, owner, data, name, ctype):
    r = upload(client, owner, data, name, ctype)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    for item in items:
        assert set(item) == {"name", "quantity", "due_date", "storage", "is_risky", "urgent_days"}


def test_mock_covers_risky_and_missing_due_date(client, owner):
    items = upload(client, owner, JPEG).json()["items"]
    assert any(i["is_risky"] for i in items)
    assert any(i["due_date"] is None for i in items)
    assert {i["storage"] for i in items} >= {"fridge", "freezer", "room"}


def test_analyze_does_not_save(client, owner):
    assert upload(client, owner, JPEG).status_code == 200
    assert client.get("/api/cards", headers=owner).json() == {"items": []}


def test_same_photo_again_is_analyzed_again(client, owner):
    assert upload(client, owner, JPEG).status_code == 200
    assert upload(client, owner, JPEG).status_code == 200


def test_not_an_image_is_rejected_even_with_image_name(client, owner):
    assert_error(upload(client, owner, b"hello world", "a.jpg", "image/jpeg"), 400, "INVALID_IMAGE")


def test_gif_is_rejected(client, owner):
    assert_error(upload(client, owner, GIF, "a.gif", "image/gif"), 400, "INVALID_IMAGE")


def test_missing_file_is_rejected(client, owner):
    assert_error(client.post(URL, headers=owner), 400, "INVALID_IMAGE")


def test_text_in_image_field_is_rejected(client, owner):
    r = client.post(URL, data={"image": "not a file"}, headers=owner)
    assert_error(r, 400, "INVALID_IMAGE")


def test_too_large_is_413(client, owner):
    big = JPEG + b"\x00" * (10 * 1024 * 1024)
    assert_error(upload(client, owner, big), 413, "IMAGE_TOO_LARGE")


def test_exactly_10mb_is_allowed(client, owner):
    data = JPEG + b"\x00" * (10 * 1024 * 1024 - len(JPEG))
    assert len(data) == 10 * 1024 * 1024
    assert upload(client, owner, data).status_code == 200


def test_owner_header_required(client):
    r = client.post(URL, files={"image": ("a.jpg", JPEG, "image/jpeg")})
    assert_error(r, 400, "OWNER_MISSING")


def test_no_food_found_is_422(client, owner, monkeypatch):
    monkeypatch.setenv("MOCK_AI_MODE", "empty")
    assert_error(upload(client, owner, JPEG), 422, "NO_FOOD_FOUND")
    assert client.get("/api/cards", headers=owner).json() == {"items": []}


def test_ai_call_failure_is_502(client, owner, monkeypatch):
    monkeypatch.setenv("MOCK_AI_MODE", "error")
    assert_error(upload(client, owner, JPEG), 502, "AI_FAILED")
    assert client.get("/api/cards", headers=owner).json() == {"items": []}


class BadShape:
    def __init__(self, items):
        self.items = items

    def analyze(self, image):
        return self.items


@pytest.mark.parametrize(
    "items",
    [
        [{"name": "우유"}],
        [{"name": "", "quantity": 1, "due_date": None, "storage": "fridge",
          "is_risky": False, "urgent_days": 1}],
        [{"name": "우유", "quantity": 1, "due_date": None, "storage": "attic",
          "is_risky": False, "urgent_days": 1}],
        ["not a dict"],
    ],
)
def test_malformed_ai_response_is_502_like_call_failure(client, owner, items):
    app.dependency_overrides[get_analyzer] = lambda: BadShape(items)
    try:
        assert_error(upload(client, owner, JPEG), 502, "AI_FAILED")
    finally:
        app.dependency_overrides.clear()
