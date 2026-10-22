import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "foods.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    name        TEXT NOT NULL,
    quantity    INTEGER NOT NULL,
    due_date    TEXT,
    storage     TEXT NOT NULL,
    is_risky    INTEGER NOT NULL,
    urgent_days INTEGER NOT NULL,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cards_owner_status ON cards (owner_id, status);

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    login_id      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions (expires_at);
"""


def db_path() -> Path:
    return Path(os.environ.get("FOODS_DB_PATH", _DEFAULT_PATH))


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(UTC).isoformat()


def list_remaining(conn: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    # ISO 날짜 문자열은 사전순이 날짜순이다. 기한이 없는 카드는 맨 아래.
    return conn.execute(
        "SELECT * FROM cards WHERE owner_id = ? AND status = 'remaining' "
        "ORDER BY due_date IS NULL, due_date, created_at, rowid",
        (owner,),
    ).fetchall()


def insert_cards(
    conn: sqlite3.Connection, owner: str, items: list[dict]
) -> list[sqlite3.Row]:
    """전체 성공 또는 전체 실패. 한 트랜잭션으로 넣는다."""
    now = _now()
    ids: list[str] = []
    with conn:
        for item in items:
            card_id = str(uuid.uuid4())
            ids.append(card_id)
            conn.execute(
                "INSERT INTO cards (id, owner_id, name, quantity, due_date, storage, "
                "is_risky, urgent_days, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'remaining', ?, ?)",
                (
                    card_id,
                    owner,
                    item["name"],
                    item["quantity"],
                    item["due_date"],
                    item["storage"],
                    int(item["is_risky"]),
                    item["urgent_days"],
                    now,
                    now,
                ),
            )
    marks = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT * FROM cards WHERE id IN ({marks})", ids
    ).fetchall()
    by_id = {r["id"]: r for r in rows}
    return [by_id[i] for i in ids]


def get_card(conn: sqlite3.Connection, owner: str, card_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM cards WHERE id = ? AND owner_id = ?", (card_id, owner)
    ).fetchone()


_EDITABLE = {"name", "quantity", "due_date", "storage", "is_risky"}


def update_card(
    conn: sqlite3.Connection, owner: str, card_id: str, changes: dict
) -> sqlite3.Row:
    """바뀐 필드만 반영하고 updated_at 을 갱신한다."""
    assert changes and set(changes) <= _EDITABLE
    values = {k: (int(v) if k == "is_risky" else v) for k, v in changes.items()}
    sets = ", ".join(f"{k} = ?" for k in values) + ", updated_at = ?"
    with conn:
        conn.execute(
            f"UPDATE cards SET {sets} WHERE id = ? AND owner_id = ?",
            (*values.values(), _now(), card_id, owner),
        )
    row = get_card(conn, owner, card_id)
    assert row is not None
    return row


def set_status(
    conn: sqlite3.Connection, owner: str, card_id: str, status: str
) -> sqlite3.Row:
    """카드를 지우지 않고 상태만 바꾼다 (D-007)."""
    with conn:
        conn.execute(
            "UPDATE cards SET status = ?, updated_at = ? WHERE id = ? AND owner_id = ?",
            (status, _now(), card_id, owner),
        )
    row = get_card(conn, owner, card_id)
    assert row is not None
    return row
