import importlib.util
import sqlite3
import uuid
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "migrate_with_backup.py"
_spec = importlib.util.spec_from_file_location("migrate_with_backup", _SCRIPT)
mwb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mwb)

OLD_SCHEMA = """
CREATE TABLE cards (
    id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, name TEXT NOT NULL,
    quantity INTEGER NOT NULL, due_date TEXT, storage TEXT NOT NULL,
    is_risky INTEGER NOT NULL, urgent_days INTEGER NOT NULL, status TEXT NOT NULL,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX idx_cards_owner_status ON cards (owner_id, status);
"""


@pytest.fixture
def old_db(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(mwb, "BACKUP_DIR", tmp_path / "backups")
    path = tmp_path / "foods.db"
    conn = sqlite3.connect(path)
    conn.executescript(OLD_SCHEMA)
    for i in range(5):
        conn.execute(
            "INSERT INTO cards VALUES (?, ?, ?, 1, ?, 'fridge', 0, 3, ?, 't', 't')",
            (
                str(uuid.uuid4()),
                str(uuid.uuid4()),
                f"식품{i}",
                None if i == 0 else "2026-11-01",
                "archived" if i == 4 else "remaining",
            ),
        )
    conn.commit()
    conn.close()
    return path


def test_migration_moves_all_cards_to_migrated_user(old_db):
    before = mwb.snapshot(old_db)
    assert mwb.main(["x", str(old_db)]) == 0
    after = mwb.snapshot(old_db)
    assert after["total"] == before["total"] == 5
    assert after["by_status"] == before["by_status"]
    assert len(after["by_owner"]) == 1
    conn = sqlite3.connect(old_db)
    users = conn.execute("SELECT login_id, password_hash FROM users").fetchall()
    assert users == [("migrated@test.com", "")]
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    conn.close()


def test_backup_is_kept_and_unchanged(old_db, tmp_path):
    before = mwb.snapshot(old_db)
    mwb.main(["x", str(old_db)])
    baks = list((tmp_path / "backups").glob("*.bak"))
    assert len(baks) == 1
    assert mwb.snapshot(baks[0]) == before


def test_mismatch_restores_backup(old_db, monkeypatch, tmp_path):
    before = mwb.snapshot(old_db)
    real_upgrade = mwb.upgrade

    def lossy(path):
        real_upgrade(path)
        if path == old_db:  # 본 DB 적용 뒤 카드 한 건이 사라지는 상황
            c = sqlite3.connect(path)
            c.execute("DELETE FROM cards WHERE rowid = 1")
            c.commit()
            c.close()

    monkeypatch.setattr(mwb, "upgrade", lossy)
    assert mwb.main(["x", str(old_db)]) == 3
    assert mwb.snapshot(old_db) == before
    conn = sqlite3.connect(old_db)
    assert conn.execute("SELECT 1 FROM sqlite_master WHERE name='users'").fetchone() is None
    conn.close()
    assert list(tmp_path.glob("foods.db.broken-*"))


def _upgrade_to(path: Path, revision: str) -> None:
    import os

    from alembic import command
    from alembic.config import Config

    os.environ["FOODS_DB_PATH"] = str(path)
    command.upgrade(Config(str(mwb.BACKEND / "alembic.ini")), revision)


def _q(path: Path, sql: str):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def test_four_steps_each_check(old_db, monkeypatch):
    monkeypatch.setenv("FOODS_DB_PATH", str(old_db))
    before = mwb.snapshot(old_db)
    cols = mwb.other_columns(old_db)

    _upgrade_to(old_db, "0001")  # 구조 추가: 카드 수·내용 그대로, 사용자 없음
    assert _q(old_db, "SELECT COUNT(*) FROM users") == [(0,)]
    assert mwb.snapshot(old_db) == before

    _upgrade_to(old_db, "0002")  # 이전용 계정: 사용자 한 명, 카드는 아직 그대로
    assert _q(old_db, "SELECT login_id, password_hash FROM users") == [("migrated@test.com", "")]
    assert mwb.snapshot(old_db) == before

    _upgrade_to(old_db, "0003")  # 주인 채우기: 주인 없는 카드 0
    assert _q(
        old_db, "SELECT COUNT(*) FROM cards WHERE owner_id NOT IN (SELECT id FROM users)"
    ) == [(0,)]
    assert mwb.snapshot(old_db)["total"] == before["total"]

    _upgrade_to(old_db, "0004")  # 필수로: 수·내용 그대로
    after = mwb.snapshot(old_db)
    assert after["total"] == before["total"] and after["ids"] == before["ids"]
    assert mwb.other_columns(old_db) == cols
    notnull = [r for r in _q(old_db, "PRAGMA table_info(cards)") if r[1] == "owner_id"]
    assert notnull[0][3] == 1


def test_step_4_stops_on_card_without_owner(old_db, monkeypatch):
    monkeypatch.setenv("FOODS_DB_PATH", str(old_db))
    _upgrade_to(old_db, "0003")
    conn = sqlite3.connect(old_db)
    conn.execute(
        "INSERT INTO cards VALUES ('orphan', 'nobody', 'x', 1, NULL, 'room', 0, 3, "
        "'remaining', 't', 't')"
    )
    conn.commit()
    conn.close()
    with pytest.raises(RuntimeError, match="0004"):
        _upgrade_to(old_db, "0004")


def test_step_2_stops_if_two_users_exist(old_db, monkeypatch):
    monkeypatch.setenv("FOODS_DB_PATH", str(old_db))
    _upgrade_to(old_db, "0001")
    conn = sqlite3.connect(old_db)
    conn.execute("INSERT INTO users VALUES ('u1', 'someone', 'h', 't')")
    conn.commit()
    conn.close()
    with pytest.raises(RuntimeError, match="0002"):
        _upgrade_to(old_db, "0002")


def test_upgrade_is_safe_on_db_created_by_app(tmp_path, monkeypatch):
    # 앱이 이미 users, sessions 를 만든 DB 에서도 적용된다.
    from backend.db import connect

    path = tmp_path / "app.db"
    monkeypatch.setenv("FOODS_DB_PATH", str(path))
    connect().close()
    mwb.upgrade(path)
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    conn.close()
