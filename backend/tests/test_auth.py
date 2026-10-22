import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.main import app

PW = "password-1234"


def signup(client, login_id="alice", password=PW):
    return client.post("/api/auth/signup", json={"login_id": login_id, "password": password})


def login(client, login_id="alice", password=PW):
    return client.post("/api/auth/login", json={"login_id": login_id, "password": password})


def db(client_path) -> sqlite3.Connection:
    return sqlite3.connect(client_path)


@pytest.fixture
def db_file(tmp_path):
    return tmp_path / "test.db"


def test_signup_logs_in_and_me_works(client):
    r = signup(client)
    assert r.status_code == 201
    user = r.json()["user"]
    assert set(user) == {"id", "login_id"} and user["login_id"] == "alice"
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "max-age=1800" in cookie
    me = client.get("/api/auth/me")
    assert me.status_code == 200 and me.json() == {"user": user}


def test_response_never_contains_password_or_hash(client, db_file):
    r = signup(client)
    assert PW not in r.text and "scrypt" not in r.text
    stored = db(db_file).execute("SELECT password_hash FROM users").fetchone()[0]
    assert stored.startswith("scrypt$") and PW not in stored


def test_login_id_is_case_insensitive_and_unique(client):
    assert signup(client, "Alice").json()["user"]["login_id"] == "alice"
    r = signup(client, "ALICE")
    assert r.status_code == 409 and r.json()["error"]["code"] == "LOGIN_ID_TAKEN"


@pytest.mark.parametrize(
    "body,field",
    [
        ({"login_id": "ab", "password": PW}, "login_id"),
        ({"login_id": "has space", "password": PW}, "login_id"),
        ({"login_id": "alice", "password": "short"}, "password"),
    ],
)
def test_signup_validation(client, body, field):
    r = client.post("/api/auth/signup", json=body)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert field in r.json()["error"]["fields"]


def test_login_and_logout_flow(client):
    signup(client)
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401

    r = login(client)
    assert r.status_code == 200 and r.json()["user"]["login_id"] == "alice"
    assert client.get("/api/auth/me").status_code == 200

    out = client.post("/api/auth/logout")
    assert out.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_old_session_is_dead_after_logout(client):
    signup(client)
    token = client.cookies.get("session")
    client.post("/api/auth/logout")
    client.cookies.set("session", token)
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/logout").status_code == 401


def test_wrong_password_and_unknown_id_look_the_same(client):
    signup(client)
    client.cookies.clear()
    a = login(client, password="wrong-password")
    b = login(client, login_id="nobody")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()
    assert a.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_empty_fields_422(client):
    r = client.post("/api/auth/login", json={"login_id": "", "password": ""})
    assert r.status_code == 422


def test_me_and_logout_need_login(client):
    for r in (client.get("/api/auth/me"), client.post("/api/auth/logout")):
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHENTICATED"


def test_session_expires_after_30_minutes(client, db_file):
    signup(client)
    conn = db(db_file)
    row = conn.execute("SELECT created_at, expires_at FROM sessions").fetchone()
    span = datetime.fromisoformat(row[1]) - datetime.fromisoformat(row[0])
    assert span == timedelta(minutes=30)
    past = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    conn.execute("UPDATE sessions SET expires_at = ?", (past,))
    conn.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_session_stored_as_hash_not_cookie_value(client, db_file):
    signup(client)
    token = client.cookies.get("session")
    ids = [r[0] for r in db(db_file).execute("SELECT id FROM sessions")]
    assert ids and token not in ids


def test_migrated_account_cannot_login_until_signup(client, db_file):
    conn = db(db_file)
    from backend.db import connect

    connect().close()
    conn.execute(
        "INSERT INTO users VALUES ('mig-id', 'migrated@test.com', '', 't')"
    )
    conn.execute(
        "INSERT INTO cards VALUES ('c1','mig-id','우유',1,NULL,'fridge',0,3,'remaining','t','t')"
    )
    conn.commit()

    assert login(client, "migrated@test.com", PW).status_code == 401

    r = signup(client, "migrated@test.com")
    assert r.status_code == 201 and r.json()["user"]["id"] == "mig-id"
    assert signup(client, "migrated@test.com").status_code == 409
    client.cookies.clear()
    assert login(client, "migrated@test.com", PW).status_code == 200
    assert login(client, "migrated@test.com", "other-password").status_code == 401


def test_server_does_not_start_without_session_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("FOODS_DB_PATH", str(tmp_path / "x.db"))
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass
