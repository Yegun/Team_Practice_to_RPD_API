import uuid
from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("FOODS_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as c:
        yield c


@pytest.fixture
def owner() -> dict[str, str]:
    return {"X-Owner-Id": str(uuid.uuid4())}


def make_item(**overrides) -> dict:
    item = {
        "name": "우유",
        "quantity": 1,
        "due_date": None,
        "storage": "fridge",
        "is_risky": False,
        "urgent_days": 3,
    }
    item.update(overrides)
    return item


def days_from_today(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()
