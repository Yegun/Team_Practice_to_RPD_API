from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("FOODS_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    with TestClient(app) as c:
        yield c


@pytest.fixture
def new_user(client):
    """가입한 사용자의 로그인 쿠키를 헤더로 돌려주는 함수. 공유 쿠키 저장소는 비운다."""

    def make(login_id: str = "alice") -> dict[str, str]:
        r = client.post(
            "/api/auth/signup", json={"login_id": login_id, "password": "password-1234"}
        )
        assert r.status_code == 201, r.text
        token = client.cookies.get("session")
        client.cookies.clear()
        return {"Cookie": f"session={token}"}

    return make


@pytest.fixture
def owner(new_user) -> dict[str, str]:
    return new_user("alice")


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
