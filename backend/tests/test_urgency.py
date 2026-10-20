from datetime import date

import pytest
from conftest import days_from_today, make_item

from backend.cards import days_left, urgency

TODAY = date(2026, 10, 20)


def test_days_left_none_when_no_due_date():
    assert days_left(None, TODAY) is None


@pytest.mark.parametrize(
    ("due", "expected"),
    [
        ("2026-10-20", 0),
        ("2026-10-23", 3),
        ("2026-10-19", -1),
        ("2026-11-01", 12),
        ("2027-01-01", 73),
    ],
)
def test_days_left(due, expected):
    assert days_left(due, TODAY) == expected


@pytest.mark.parametrize(
    ("left", "urgent_days", "expected"),
    [
        (None, 3, "unknown"),
        (-1, 3, "expired"),
        (0, 3, "urgent"),
        (3, 3, "urgent"),
        (4, 3, "ok"),
        (0, 1, "urgent"),
        (2, 1, "ok"),
    ],
)
def test_urgency(left, urgent_days, expected):
    assert urgency(left, urgent_days) == expected


def test_api_reports_urgency_per_card_threshold(client, owner):
    # 같은 3일 남은 카드라도 urgent_days 에 따라 임박 여부가 다르다 (D-014, D-017).
    items = [
        make_item(name="짧은기준", due_date=days_from_today(3), urgent_days=1),
        make_item(name="긴기준", due_date=days_from_today(3), urgent_days=5),
        make_item(name="오늘", due_date=days_from_today(0)),
        make_item(name="지남", due_date=days_from_today(-1)),
        make_item(name="없음"),
    ]
    client.post("/api/cards", json={"items": items}, headers=owner)
    cards = client.get("/api/cards", headers=owner).json()["items"]
    by_name = {c["name"]: c for c in cards}
    assert by_name["짧은기준"]["urgency"] == "ok"
    assert by_name["긴기준"]["urgency"] == "urgent"
    assert by_name["오늘"]["days_left"] == 0
    assert by_name["오늘"]["urgency"] == "urgent"
    assert by_name["지남"]["days_left"] == -1
    assert by_name["지남"]["urgency"] == "expired"
    assert by_name["없음"]["days_left"] is None
    assert by_name["없음"]["urgency"] == "unknown"
